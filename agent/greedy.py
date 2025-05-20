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
        possible_moves = []

        if self._color == PlayerColor.RED:
            allowed_directions = {
                Direction.Right, Direction.Left,
                Direction.Down, Direction.DownLeft, Direction.DownRight
            }
        else:  # BLUE
            allowed_directions = {
                Direction.Right, Direction.Left,
                Direction.Up, Direction.UpLeft, Direction.UpRight
            }

        all_frogs = self.red_frogs | self.blue_frogs

        for frog in self.frogs:
            start_row = frog.r
            # 1-step moves
            for direction in allowed_directions:
                dest = apply_direction(frog, direction)
                if dest in self.lily_pads and dest not in all_frogs:
                    # Score = 1 step (length=1) + forward progress
                    step_score = 1 + self._forward_progress(start_row, dest.r)
                    possible_moves.append((MoveAction(frog, [direction]), step_score))

            # jumps
            jumps = find_jumps(frog, frog, allowed_directions, all_frogs, self.lily_pads, {frog}, [])
            for path in jumps:
                # simulate final landing
                current = frog
                for d in path:
                    over = apply_direction(current, d)
                    current = apply_direction(over, d)
                landing_row = current.r

                length = len(path)       # number of jumps chained
                progress = self._forward_progress(start_row, landing_row)
                jump_score = length * 2 + progress   # you can weight length more heavily
                possible_moves.append((MoveAction(frog, path), jump_score))
                
        # pick the move with maximum score (break ties randomly)
        if possible_moves:
            # shuffle before sort to randomize equal-scored moves
            random.shuffle(possible_moves)
            best_move, best_score = max(possible_moves, key=lambda ms: ms[1])
            return best_move
        else:
            return GrowAction()    
    
    def _forward_progress(self, start_row: int, dest_row: int) -> int:
        # For RED, higher row index is closer to goal; for BLUE, lower.
        if self._color == PlayerColor.RED:
            return dest_row - start_row
        else:
            return start_row - dest_row
            
    def update(self, color: PlayerColor, action: Action, **referee: dict):
        if isinstance(action, MoveAction):
            current = action.coord
            for direction in action.directions:
                current = apply_direction(current, direction)
                if current in self.red_frogs or current in self.blue_frogs:
                    current = apply_direction(current, direction)
            
            destination = current
            
            self.lily_pads.discard(action.coord)

            # Update frog positions based on which player moved
            if color == PlayerColor.RED:
                self.red_frogs.discard(action.coord) 
                self.red_frogs.add(destination)
            else:  # PlayerColor.BLUE
                self.blue_frogs.discard(action.coord)
                self.blue_frogs.add(destination)

        elif isinstance(action, GrowAction):
            # Determine which frogs are growing
            frogs = self.red_frogs if color == PlayerColor.RED else self.blue_frogs
            for frog in frogs:
                for adj in adjacent_coords(frog):
                    self.lily_pads.add(adj)        
            
        
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
        return Coord(new_r, new_c)
    return None

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

def find_jumps(start: Coord, current: Coord, directions: set[Direction], frogs: set[Coord], lily_pads: set[Coord], visited: set[Coord], path: list[Direction]):
    all_paths = []

    for direction in directions:
        over = apply_direction(current, direction)
        dest = apply_direction(over, direction) if over else None

        if (
            dest and
            over in frogs and
            dest in lily_pads and
            dest not in frogs and
            dest not in visited
        ):
            new_path = path + [direction]
            next_lilypads = lily_pads - {current}
            next_frogs = (frogs - {current}) | {dest}

            # Recursively find extensions
            extended_paths = find_jumps(start, dest, directions, next_frogs, next_lilypads, visited | {dest}, new_path)
            if extended_paths:
                all_paths.extend(extended_paths)
            else:
                all_paths.append(new_path)

    return all_paths

