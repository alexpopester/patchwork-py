import json

# TODO: put what I actually need
from game_structs import (
    PAYDAY_LOCATIONS,
    PIECE_DEFS,
    TOTAL_TIME_AVAILABLE,
    GeneralOptions,
    PatchQueue,
    Piece,
    PlayerChoice,
    SingleGameResults,
)
from players import (
    MostEdgesTouching,
    Player,
    RandomChoice,
)


def generic_play(
    piece_queue: PatchQueue, player_list: list[Player], print_results: bool = True
) -> SingleGameResults:
    next_player_index = 0
    player_order = [
        player_list[i].piece_location for i in range(len(player_list))]
    count = 0
    player_index_who_has_achieved_goal = -1
    while any(player.piece_location < TOTAL_TIME_AVAILABLE for player in player_list):
        count += 1
        current_player: Player = player_list[next_player_index]
        previous_location = current_player.piece_location
        options = piece_queue.get_lookaheads()
        real_options = []
        # TODO: maybe a better way to do this mapping
        real_options_to_indices = []
        for index, piece in enumerate(options):
            if (
                piece.button_cost <= current_player.button_count
                and current_player.button_count >= 0
            ):
                real_options.append(piece)
                real_options_to_indices.append(index)
        player_choice: PlayerChoice = (
            current_player.make_choice(real_options)
            if len(real_options) > 0
            else PlayerChoice(
                piece_index=GeneralOptions.SKIP,
                piece_orientation_index=-1,
                location=(-1, -1),
            )
        )
        if player_choice.piece_index == GeneralOptions.SKIP:
            if len(player_list) <= 1:
                current_player.button_count += 1
                current_player.piece_location += 1
            else:
                # TODO: determine whether max or min is a better system for more than 2
                piece_to_skip_past_location = max(player_order)
                increase = (
                    piece_to_skip_past_location - current_player.piece_location
                ) + 1
                current_player.button_count += increase
                current_player.piece_location += increase
        else:
            # TODO: fix place_piece to take coordinate pair
            played_piece: Piece = piece_queue.pop_piece(
                real_options_to_indices[player_choice.piece_index]
            )
            current_player.patch_board.place_piece(
                player_choice.location[0],
                player_choice.location[1],
                played_piece.shape_combinations[player_choice.piece_orientation_index],
                played_piece.income,
            )
            current_player.button_count -= played_piece.button_cost
            current_player.piece_location += played_piece.time_cost
        player_order[next_player_index] = current_player.piece_location
        next_player_index = player_order.index(min(player_order))
        for payday in PAYDAY_LOCATIONS:
            if previous_location < payday and current_player.piece_location >= payday:
                current_player.button_count += current_player.patch_board.total_income
    if print_results:
        print("GAME COMPLETE")
    player_results = []
    player_who_won_index = -1
    best_score = None
    for i, player in enumerate(player_list):
        if print_results:
            print(
                f"Player: '{player.name}' (P{i + 1}) finished with {
                    player.get_score()
                } points and the following board:\n{player.patch_board}"
            )
        player_results.append(player.get_score())
        # TODO: handle ties?
        if best_score is None or best_score < player_results[i]:
            player_who_won_index = i
            best_score = player_results[i]
    win_statuses = [False] * len(player_list)
    win_statuses[player_who_won_index] = True
    # TODO: Need to do goal determinations
    goal_statuses = [False] * len(player_list)
    return SingleGameResults(
        player_scores=player_results,
        player_win_statuses=win_statuses,
        player_achieved_goal=goal_statuses,
    )


def main():
    print("Hello from patchwork-py!")
    # NOTE: uncomment to have repeated results
    # random.seed(15)
    with open(PIECE_DEFS, "r") as file:
        pieces = json.loads(file.read())
    piece_queue = []
    for piece in pieces:
        new_piece = Piece(**piece)
        piece_queue.append(new_piece)

    rounds_to_play = 1000
    player_1 = MostEdgesTouching()
    player_2 = RandomChoice()
    player_list: list[Player] = [player_1, player_2]
    all_scores = [[] for _ in range(len(player_list))]
    all_wins = [[] for _ in range(len(player_list))]
    all_goal_achievements = [[] for _ in range(len(player_list))]
    patch_queue = PatchQueue(piece_queue, randomize_queue=True)
    print("--- STARTING GAMES ---")
    for i in range(rounds_to_play):
        single_game_results: SingleGameResults = generic_play(
            patch_queue, player_list, print_results=False
        )
        # print(f"RESULTS{i}: {single_game_results}")
        for j in range(len(single_game_results.player_scores)):
            #    print(f"APPENDING TO {j}: {single_game_results.player_scores[j]}")
            all_scores[j].append(single_game_results.player_scores[j])
            all_wins[j].append(single_game_results.player_win_statuses[j])
            all_goal_achievements[j].append(
                single_game_results.player_achieved_goal[j])
            player_list[j].reset_player()
        patch_queue.reset_randomize_queue()
        if i % 100 == 0:
            print(f"GAME {i} COMPLETE...")
    print("--- GAMES COMPLETE ---")
    for i, player in enumerate(player_list):
        print(
            f"{player.name} (P{i + 1}) averaged: {
                sum(all_scores[i]) / rounds_to_play
            }, won {sum(all_wins[i])} rounds, and won {
                sum(all_goal_achievements[i])
            } goals over {rounds_to_play} games."
        )


if __name__ == "__main__":
    main()
