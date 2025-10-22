from copy import deepcopy
from enum import Enum, IntEnum
from random import shuffle

from pydantic import BaseModel

FILLED_SQUARE = " ▣"
EMPTY_SQUARE = " □"
# GAME PARAMS
BOARD_SIZE = 9  # Always a square
PIECE_DEFS = "piece_defs.json"  # Always a square
TOTAL_TIME_AVAILABLE = 53  # Per my counting of the board
# TODO: could code it to be a start and step size. Not sure which is more fun
PAYDAY_LOCATIONS = [5, 11, 17, 23, 29, 35, 41, 47, 53]
FIRST_PAYDAY = 5
PAYDAY_STEP = 6
# TODO: same thing here but would have to do something different for the gap
LEATHER_LOCATIONS = [20, 26, 32, 44, 50]
PIECES_TO_LOOKAHEAD = 3
START_BUTTON_COUNT = 5
SHAPE_TO_MAKE_ROWS = 7
SHAPE_TO_MAKE_COLS = 7
FIRST_TO_MEET_GOAL_BONUS = 7
# END GAME PARAMS


class Rotation(Enum):
    # TODO: make these functions or something like that.
    ZERO = 0
    PI_HALF = 90
    PI = 180
    THREE_PI_HALVES = 270


class GeneralOptions(IntEnum):
    SKIP = -1


class SingleGameResults(BaseModel):
    player_scores: list[int]
    player_win_statuses: list[bool]
    player_achieved_goal: list[bool]


class PieceOrientation(BaseModel):
    shape: list
    rotation: Rotation
    is_flipped: bool

    def __str__(self):
        shape_representation = "\n"
        for i, row in enumerate(self.shape):
            for val in row:
                shape_representation += FILLED_SQUARE if val else EMPTY_SQUARE
            if i + 1 < len(self.shape):
                shape_representation += "\n"
        return shape_representation


class PossiblePlayCoordinates(BaseModel):
    x_coordinate: int
    y_coordinate: int
    squares_to_fill: list[tuple[int, int]] | None


class IsValidPlayModel(BaseModel):
    is_valid_play: bool
    squares_to_fill: list[tuple[int, int]] | None


class PlayerChoice(BaseModel):
    piece_index: int
    piece_orientation_index: int
    location: tuple[int, int]


class Piece:
    def __init__(
        self,
        shape: list[list],
        income: int,
        time_cost: int,
        button_cost: int,
        is_start_piece: bool = False,
    ):
        self.shape = shape
        self.shape_combinations: list[PieceOrientation] = []
        self.income = income
        self.time_cost = time_cost
        self.button_cost = button_cost
        self.is_start_piece = is_start_piece
        self.populate_shape_permutations()

    def __repr__(self):
        shape_representation = "\n"
        for i, row in enumerate(self.shape):
            for val in row:
                shape_representation += FILLED_SQUARE if val else EMPTY_SQUARE
            if i + 1 < len(self.shape):
                shape_representation += "\n"
        return shape_representation

    def populate_shape_permutations(self):
        for rotation in Rotation:
            for is_flipped in [False, True]:
                new_shape = self.get_rotation_shape(rotation)
                if is_flipped:
                    self.flip_shape(new_shape)
                self.shape_combinations.append(
                    PieceOrientation(
                        shape=new_shape, rotation=rotation, is_flipped=is_flipped
                    )
                )

    def get_rotation_shape(self, rotation: Rotation = Rotation.ZERO):
        if rotation == Rotation.PI_HALF:
            max_col_size = max([len(self.shape[i])
                               for i in range(len(self.shape))])
            new_shape = [[False] * len(self.shape)
                         for _ in range(max_col_size)]
            for i in range(len(self.shape)):
                for j in range(len(self.shape[i])):
                    new_shape[j][i] = self.shape[i][j]
            new_shape.reverse()
        elif rotation == Rotation.PI:
            max_col_size = max([len(self.shape[i])
                               for i in range(len(self.shape))])
            new_shape = [
                [False] * max_col_size for _ in range(len(self.shape))]
            for i in range(len(self.shape)):
                for j in range(len(self.shape[i])):
                    new_shape[len(new_shape) - (i + 1)][j] = self.shape[i][j]
        elif rotation == Rotation.THREE_PI_HALVES:
            max_col_size = max([len(self.shape[i])
                               for i in range(len(self.shape))])
            new_shape = [[False] * len(self.shape)
                         for _ in range(max_col_size)]
            for i in range(len(self.shape)):
                for j in range(len(self.shape[i])):
                    new_shape[j][i] = self.shape[i][j]
            for row in new_shape:
                row.reverse()
        else:
            max_col_size = max([len(self.shape[i])
                               for i in range(len(self.shape))])
            new_shape = [
                [False] * max_col_size for _ in range(len(self.shape))]
            for i in range(len(self.shape)):
                for j in range(len(self.shape[i])):
                    new_shape[i][j] = self.shape[i][j]
        return new_shape

    def flip_shape(self, shape: list):
        shape.reverse()


class PatchBoard:
    def __init__(self):
        self.board = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.total_income = 0
        # print(board)

    def place_piece(self, x: int, y: int, piece: PieceOrientation, income_to_add: int):
        new_board = deepcopy(self.board)
        for i, row in enumerate(piece.shape):
            for j, col in enumerate(row):
                if col and (
                    x + i >= BOARD_SIZE
                    or y + j >= BOARD_SIZE
                    or (self.board[x + i][y + j])
                ):
                    raise Exception(
                        f"BAD PLACEMENT:\n{self}\nattempted, ({x},{y}), \nwith piece{
                            piece
                        }\n\n{
                            self.get_possible_plays_for_a_piece(
                                piece=piece, capture_squares_filled=True
                            )
                        }"
                    )
                elif col:
                    new_board[x + i][y + j] = col or self.board[x + i][y + j]
        self.total_income += income_to_add
        self.board = new_board

    def is_piece_able_to_be_placed(
        self,
        x: int,
        y: int,
        piece: PieceOrientation,
        capture_squares_filled: bool = False,
    ) -> IsValidPlayModel:
        squares_to_fill = []
        for i, row in enumerate(piece.shape):
            for j, col in enumerate(row):
                squares_to_fill.append((x + i, y + j))
                if (
                    x + i >= BOARD_SIZE
                    or y + j >= BOARD_SIZE
                    or (self.board[x + i][y + j] and col)
                ):
                    return IsValidPlayModel(
                        is_valid_play=False, squares_to_fill=squares_to_fill
                    )
        return IsValidPlayModel(is_valid_play=True, squares_to_fill=squares_to_fill)

    def get_possible_plays_for_a_piece(
        self, piece: PieceOrientation, capture_squares_filled: bool = False
    ):
        plays_array = []
        for x in range(BOARD_SIZE):
            for y in range(BOARD_SIZE):
                result = self.is_piece_able_to_be_placed(
                    x, y, piece, capture_squares_filled
                )
                # TODO: fix the output of is_piece_able_to_be_placed. It's messy
                if capture_squares_filled and result.is_valid_play:
                    plays_array.append(
                        PossiblePlayCoordinates(
                            x_coordinate=x,
                            y_coordinate=y,
                            squares_to_fill=result.squares_to_fill,
                        )
                    )
                elif not capture_squares_filled and result.is_valid_play:
                    plays_array.append(
                        PossiblePlayCoordinates(
                            x_coordinate=x, y_coordinate=y, squares_to_fill=None
                        )
                    )
        return plays_array

    def get_empty_square_count(self):
        count = 0
        for row in self.board:
            for col in row:
                count += 1 if not col else 0
        return count

    def has_achieved_goal(self):
        pass

    def __repr__(self):
        shape_representation = ""
        for i, row in enumerate(self.board):
            for val in row:
                shape_representation += FILLED_SQUARE if val else EMPTY_SQUARE
            if i + 1 < len(self.board):
                shape_representation += "\n"
        shape_representation += f"\nINCOME: {self.total_income}\n"
        return shape_representation


class PatchQueue:
    def __init__(self, patch_array: list, randomize_queue: bool = False):
        self.current_index = 0
        self.patch_array = patch_array
        self.gold_copy_patch_queue = deepcopy(patch_array)
        if randomize_queue:
            shuffle(self.patch_array)
        for i in range(len(patch_array)):
            if patch_array[i].is_start_piece:
                self.current_index = (i + 1) % len(self.patch_array)

    def reset_randomize_queue(self):
        self.patch_array = deepcopy(self.gold_copy_patch_queue)
        shuffle(self.patch_array)
        for i in range(len(self.patch_array)):
            if self.patch_array[i].is_start_piece:
                self.current_index = (i + 1) % len(self.patch_array)

    def get_lookaheads(self):
        lookaheads = []
        for i in range(PIECES_TO_LOOKAHEAD):
            # Wrap around case
            lookaheads.append(
                self.patch_array[(self.current_index + i) %
                                 len(self.patch_array)]
            )
        return lookaheads

    def pop_piece(self, selection_index: int):
        played_piece = self.patch_array.pop(
            (self.current_index + selection_index) % len(self.patch_array)
        )
        self.current_index += selection_index
        return played_piece
