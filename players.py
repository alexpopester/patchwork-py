from random import randint, randrange

from pydantic import BaseModel

from game_structs import (
    BOARD_SIZE,
    FIRST_TO_MEET_GOAL_BONUS,
    START_BUTTON_COUNT,
    GeneralOptions,
    PatchBoard,
    Piece,
    PieceOrientation,
    PlayerChoice,
    PossiblePlayCoordinates,
)


class Player:
    name = "Player"

    def __init__(self):
        self.patch_board = PatchBoard()
        self.piece_location = 0
        self.button_count = START_BUTTON_COUNT

    def get_score(self, is_first_to_meet_goal: bool = False):
        if is_first_to_meet_goal:
            self.button_count += FIRST_TO_MEET_GOAL_BONUS
        return self.button_count + (self.patch_board.get_empty_square_count() * -2)

    def reset_player(self):
        self.patch_board = PatchBoard()
        self.piece_location = 0
        self.button_count = START_BUTTON_COUNT

    def make_choice(self, options) -> PlayerChoice:
        raise NotImplementedError


class AlwaysSkip(Player):
    name = "Always Skipt"

    def make_choice(self, options) -> PlayerChoice:
        return PlayerChoice(
            piece_index=GeneralOptions.SKIP.value,
            piece_orientation_index=-1,
            location=(-1, -1),
        )


class FirstChoice(Player):
    name = "First Choice"

    def make_choice(self, options) -> PlayerChoice:
        for i, piece in enumerate(options):
            for k in range(BOARD_SIZE):
                for j in range(BOARD_SIZE):
                    for _ in range(4):
                        piece_orientation_index = randrange(
                            len(piece.shape_combinations)
                        )
                        piece_orientation = piece.shape_combinations[
                            piece_orientation_index
                        ]
                        possible_plays: list[PossiblePlayCoordinates] = (
                            self.patch_board.get_possible_plays_for_a_piece(
                                piece_orientation
                            )
                        )
                        if len(possible_plays) > 0:
                            location = (
                                possible_plays[0].x_coordinate,
                                possible_plays[0].y_coordinate,
                            )
                            return PlayerChoice(
                                piece_index=i,
                                piece_orientation_index=piece_orientation_index,
                                location=location,
                            )
        return PlayerChoice(
            piece_index=GeneralOptions.SKIP.value,
            piece_orientation_index=-1,
            location=(-1, -1),
        )


# Picks Random piece and randomly orients it a certain number of times
# TODO: just make random choice from options
class RandomChoice(Player):
    DIFFERENT_PIECE_TRIES = 6
    SINGLE_PIECE_TRIES = 30

    name = "Random Choice"

    def make_choice(self, options: list[Piece]) -> PlayerChoice:
        for _ in range(self.DIFFERENT_PIECE_TRIES):
            piece_to_try_index = randint(0, len(options) - 1)
            piece = options[piece_to_try_index]
            piece_orientation_to_try_index = randint(
                0, len(piece.shape_combinations) - 1
            )
            piece_orientation: PieceOrientation = piece.shape_combinations[
                piece_orientation_to_try_index
            ]
            # coordinates = self.do_placement(piece, piece_orientation)
            placement_options = self.patch_board.get_possible_plays_for_a_piece(
                piece=piece_orientation, capture_squares_filled=True
            )
            if len(placement_options) > 0:
                placement_selection_index = randrange(
                    0, len(placement_options))
                placement_selection: PossiblePlayCoordinates = placement_options[
                    placement_selection_index
                ]
                return PlayerChoice(
                    piece_index=piece_to_try_index,
                    piece_orientation_index=piece_orientation_to_try_index,
                    location=(
                        placement_selection.x_coordinate,
                        placement_selection.y_coordinate,
                    ),
                )
        return PlayerChoice(
            piece_index=GeneralOptions.SKIP.value,
            piece_orientation_index=-1,
            location=(-1, -1),
        )


class BestEdgeCombo(BaseModel):
    squares_touching: int
    piece_index: int
    piece_orientation_index: int
    placement_coordinates: tuple[int, int]


class MostEdgesTouching(Player):
    name = "Most Edges Touching"

    def make_choice(self, options: list[Piece]) -> PlayerChoice:
        optimal_squares_to_fill = []
        for x in range(BOARD_SIZE):
            for y in range(BOARD_SIZE):
                if not self.patch_board.board[x][y]:
                    continue
                if x - 1 >= 0 and not self.patch_board.board[x - 1][y]:
                    optimal_squares_to_fill.append((x - 1, y))
                if x + 1 < BOARD_SIZE and not self.patch_board.board[x + 1][y]:
                    optimal_squares_to_fill.append((x + 1, y))
                if y - 1 >= 0 and not self.patch_board.board[x][y - 1]:
                    optimal_squares_to_fill.append((x, y - 1))
                if y + 1 < BOARD_SIZE and not self.patch_board.board[x][y + 1]:
                    optimal_squares_to_fill.append((x, y + 1))
        is_initial_play = False
        if len(optimal_squares_to_fill) == 0:
            is_initial_play = True
        # TODO: make an initial best combo method for this
        best_combo = BestEdgeCombo(
            squares_touching=-1,
            piece_index=-1,
            piece_orientation_index=-1,
            placement_coordinates=(-1, -1),
        )
        for i in range(len(options)):
            piece = options[i]
            for j in range(len(piece.shape_combinations)):
                possible_plays_array = self.patch_board.get_possible_plays_for_a_piece(
                    piece.shape_combinations[j], capture_squares_filled=True
                )
                if is_initial_play:
                    inital_play: PossiblePlayCoordinates = possible_plays_array[0]
                    return PlayerChoice(
                        piece_index=i,
                        piece_orientation_index=j,
                        location=(inital_play.x_coordinate,
                                  inital_play.y_coordinate),
                    )
                for possible_play in possible_plays_array:
                    touching_count = 0
                    for coordinate_pair in possible_play.squares_to_fill:
                        if coordinate_pair in optimal_squares_to_fill:
                            touching_count += 1
                    if touching_count > best_combo.squares_touching:
                        best_combo = BestEdgeCombo(
                            squares_touching=touching_count,
                            piece_index=i,
                            piece_orientation_index=j,
                            placement_coordinates=(
                                possible_play.x_coordinate,
                                possible_play.y_coordinate,
                            ),
                        )
        return PlayerChoice(
            piece_index=best_combo.piece_index,
            piece_orientation_index=best_combo.piece_orientation_index,
            location=best_combo.placement_coordinates,
        )


class MinimizeTimeThenMostEdgesTouchingWithSelectedPiece(Player):
    name = "Minimize Time then Maximize Edges Touching"

    def make_choice(self, options: list[Piece]) -> PlayerChoice:
        optimal_squares_to_fill = []
        for x in range(BOARD_SIZE):
            for y in range(BOARD_SIZE):
                if not self.patch_board.board[x][y]:
                    continue
                if x - 1 >= 0 and not self.patch_board.board[x - 1][y]:
                    optimal_squares_to_fill.append((x - 1, y))
                if x + 1 < BOARD_SIZE and not self.patch_board.board[x + 1][y]:
                    optimal_squares_to_fill.append((x + 1, y))
                if y - 1 >= 0 and not self.patch_board.board[x][y - 1]:
                    optimal_squares_to_fill.append((x, y - 1))
                if y + 1 < BOARD_SIZE and not self.patch_board.board[x][y + 1]:
                    optimal_squares_to_fill.append((x, y + 1))
        is_initial_play = False
        if len(optimal_squares_to_fill) == 0:
            is_initial_play = True
        # TODO: make an initial best combo method for this
        best_combo = BestEdgeCombo(
            squares_touching=-1,
            piece_index=-1,
            piece_orientation_index=-1,
            placement_coordinates=(-1, -1),
        )
        rank_pieces_by_time = sorted(
            options, key=lambda piece: piece.time_cost)
        for piece in rank_pieces_by_time:
            piece_index = options.index(piece)
            for j in range(len(piece.shape_combinations)):
                possible_plays_array = self.patch_board.get_possible_plays_for_a_piece(
                    piece.shape_combinations[j], capture_squares_filled=True
                )
                if is_initial_play:
                    inital_play: PossiblePlayCoordinates = possible_plays_array[0]
                    return PlayerChoice(
                        piece_index=piece_index,
                        piece_orientation_index=j,
                        location=(inital_play.x_coordinate,
                                  inital_play.y_coordinate),
                    )
                for possible_play in possible_plays_array:
                    touching_count = 0
                    for coordinate_pair in possible_play.squares_to_fill:
                        if coordinate_pair in optimal_squares_to_fill:
                            touching_count += 1
                    if touching_count > best_combo.squares_touching:
                        best_combo = BestEdgeCombo(
                            squares_touching=touching_count,
                            piece_index=piece_index,
                            piece_orientation_index=j,
                            placement_coordinates=(
                                possible_play.x_coordinate,
                                possible_play.y_coordinate,
                            ),
                        )
            return PlayerChoice(
                piece_index=best_combo.piece_index,
                piece_orientation_index=best_combo.piece_orientation_index,
                location=best_combo.placement_coordinates,
            )
        # NOTE: this one will be a skip if nothing works out.
        return PlayerChoice(
            piece_index=best_combo.piece_index,
            piece_orientation_index=best_combo.piece_orientation_index,
            location=best_combo.placement_coordinates,
        )


class CheapestPieceRandomPlacement(Player):
    SINGLE_PIECE_TRIES = 30
    name = "Cheapest Piece Random Choice"

    def make_choice(self, options: list[Piece]) -> PlayerChoice:
        rank_pieces_by_button_cost = sorted(
            options, key=lambda piece: piece.button_cost
        )
        for small_button_cost_piece in rank_pieces_by_button_cost:
            piece_to_try_index = options.index(small_button_cost_piece)
            piece = options[piece_to_try_index]
            piece_orientation_to_try_index = randint(
                0, len(piece.shape_combinations) - 1
            )
            piece_orientation: PieceOrientation = piece.shape_combinations[
                piece_orientation_to_try_index
            ]
            # coordinates = self.do_placement(piece, piece_orientation)
            placement_options = self.patch_board.get_possible_plays_for_a_piece(
                piece=piece_orientation, capture_squares_filled=True
            )
            if len(placement_options) > 0:
                placement_selection_index = randrange(
                    0, len(placement_options))
                placement_selection: PossiblePlayCoordinates = placement_options[
                    placement_selection_index
                ]
                return PlayerChoice(
                    piece_index=piece_to_try_index,
                    piece_orientation_index=piece_orientation_to_try_index,
                    location=(
                        placement_selection.x_coordinate,
                        placement_selection.y_coordinate,
                    ),
                )
        return PlayerChoice(
            piece_index=GeneralOptions.SKIP.value,
            piece_orientation_index=-1,
            location=(-1, -1),
        )
