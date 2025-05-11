# COMP30024 Artificial Intelligence, Semester 1 2025
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, MoveAction, GrowAction

import random

class Agent:
    """
    This class is the "entry point" for your agent, providing an interface to
    respond to various Freckers game events.
    """

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        This constructor method runs when the referee instantiates the agent.
        Any setup and/or precomputation should be done here.
        """
        self._color = color
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")

        # Starting frog positions
        self.red_frogs = {Coord(0, i) for i in range(1, 7)}
        self.blue_frogs = {Coord(7, i) for i in range(1, 7)}

        # Determine own and opponent frogs
        self.frogs = self.red_frogs if self._color == PlayerColor.RED else self.blue_frogs
        self.opponent_frogs = self.blue_frogs if self._color == PlayerColor.RED else self.red_frogs

        # Starting lily pads
        self.lily_pads = {
            Coord(0, 0), Coord(0, 7),
            *{Coord(1, c) for c in range(1, 7)},
            *{Coord(6, c) for c in range(1, 7)},
            Coord(7, 0), Coord(7, 7)
        }            
        
    def action(self, **referee: dict) -> Action:
        # Try all possible random MOVE actions first
        possible_moves = []

        if self._color == PlayerColor.RED:
            allowed_directions = {
                Direction.Right, Direction.Left,
                Direction.Down, Direction.DownLeft, Direction.DownRight
            }
        else:
            allowed_directions = {
                Direction.Right, Direction.Left,
                Direction.Up, Direction.UpLeft, Direction.UpRight
            }

        all_frogs = self.red_frogs | self.blue_frogs

        for frog in self.frogs:
            # One-step adjacent moves
            for direction in allowed_directions:
                dest = apply_direction(frog, direction)
                if dest in self.lily_pads and dest not in all_frogs:
                    possible_moves.append(MoveAction(frog, [direction]))

            # Multi-jump sequences
            jump_paths = find_jump_paths(frog, allowed_directions, all_frogs, self.lily_pads)
            for path in jump_paths:
                if is_valid_jump(frog, path, all_frogs, self.lily_pads):
                    possible_moves.append(MoveAction(frog, path))
                else:
                    print(f"[DEBUG] Skipped invalid jump from {frog}: {path}")
                    
        if possible_moves:
            rando = random.choice(possible_moves)
            print(f"[DEBUG]  Randomly selected move: {rando}")
            print_board(self.red_frogs, self.blue_frogs, self.lily_pads)
            return rando
            # return random.choice(possible_moves)
        else:
            return GrowAction()
    
    def update(self, color: PlayerColor, action: Action, **referee: dict):
        # print(f"[UPDATE] {color.name} played {action}")
        # print_board(self.red_frogs, self.blue_frogs, self.lily_pads)

        if isinstance(action, MoveAction):
            current = action.coord
            for direction in action.directions:
                next_coord = apply_direction(current, direction)
                if next_coord is None:
                    raise ValueError(f"Invalid move step from {current} via {direction}")
                current = next_coord
            destination = current

            # Update lily pads
            self.lily_pads.discard(action.coord)
            self.lily_pads.add(destination)

            # Update frog positions
            if color == PlayerColor.RED:
                self.red_frogs.discard(action.coord)
                self.red_frogs.add(destination)
            else:
                self.blue_frogs.discard(action.coord)
                self.blue_frogs.add(destination)

        elif isinstance(action, GrowAction):
            frogs = self.red_frogs if color == PlayerColor.RED else self.blue_frogs
            for frog in frogs:
                for adj in adjacent_coords(frog):
                    if adj not in self.lily_pads:
                        self.lily_pads.add(adj)

        # Recompute current player's frog set references
        self.frogs = self.red_frogs if self._color == PlayerColor.RED else self.blue_frogs
        self.opponent_frogs = self.blue_frogs if self._color == PlayerColor.RED else self.red_frogs


def adjacent_coords(coord: Coord) -> list[Coord]:
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]
    result = [] 
    for dr, dc in directions: 
        nr, nc = coord.r + dr, coord.c + dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            result.append(Coord(nr, nc))
    return result

def apply_direction(coord: Coord, direction: Direction) -> Coord | None:
    dr, dc = direction.value
    new_r, new_c = coord.r + dr, coord.c + dc
    if 0 <= new_r < 8 and 0 <= new_c < 8:
        if abs(new_r - coord.r) <= 1 and abs(new_c - coord.c) <= 1:
            return Coord(new_r, new_c)
    return None

def find_jump_paths(start: Coord, directions: set[Direction], frogs: set[Coord], lily_pads: set[Coord]) -> list[list[Direction]]:
    """
    Recursively finds all valid jump sequences from the starting Coord.
    Returns a list of direction sequences (each is a list of Direction).
    Now includes debug checks to prevent illegal moves and inspect logic.
    """
    paths = []

    def dfs(current: Coord, path: list[Direction], visited: set[Coord], available_lilypads: set[Coord]):
        for direction in directions:
            over = apply_direction(current, direction)
            if over is None or over not in frogs:
                continue

            dest = apply_direction(over, direction)
            if (
                dest is None or
                dest in frogs or
                dest in visited or
                dest not in available_lilypads
            ):
                continue

            new_path = path + [direction, direction]
            paths.append(new_path)

            # Simulate lily pad disappearance from current
            next_lilypads = available_lilypads - {current}
            dfs(dest, new_path, visited | {dest}, next_lilypads)

    dfs(start, [], {start}, lily_pads)
    return paths
    
def print_board(red_frogs, blue_frogs, lily_pads):
    """
    Print the 8x8 board using:
    - 'R' for red frogs
    - 'B' for blue frogs
    - '*' for lily pads
    - '.' for empty cells
    """
    board = [["." for _ in range(8)] for _ in range(8)]

    for coord in lily_pads:
        board[coord.r][coord.c] = "*"
    for coord in red_frogs:
        board[coord.r][coord.c] = "R"
    for coord in blue_frogs:
        board[coord.r][coord.c] = "B"

    print("\nBoard State:")
    for row in board:
        print(" ".join(row))
    print()

def is_valid_jump(start: Coord, directions: list[Direction], frogs: set[Coord], lily_pads: set[Coord]) -> bool:
    """
    Simulate a jump and confirm that every jump step:
    - Jumps over a frog
    - Lands on an unoccupied lily pad
    - Doesn't wrap off the board
    """
    current = start
    temp_lilypads = lily_pads.copy()

    #check if the jump doesnt wrap off the board
    if not all(0 <= apply_direction(current, dir).r < 8 and 0 <= apply_direction(current, dir).c < 8 for dir in directions):
        print(f"[INVALID] Jump failed: out of bounds")
        return False

    for i in range(0, len(directions), 2):
        dir1, dir2 = directions[i], directions[i+1]
        assert dir1 == dir2, f"Expected direction pairs, got {dir1}, {dir2}"

        over = apply_direction(current, dir1)
        if over is None or over not in frogs:
            print(f"[INVALID] Jump failed: no frog to jump over at {over}")
            return False

        dest = apply_direction(over, dir2)
        if (
            dest is None or
            dest in frogs or
            dest not in temp_lilypads
        ):
            print(f"[INVALID] Jump failed: dest invalid at {dest}")
            return False

        temp_lilypads.discard(current)  # simulate pad disappearance
        current = dest

    return True