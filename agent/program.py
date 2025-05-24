# COMP30024 Artificial Intelligence, Semester 1 2025
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, MoveAction, GrowAction

class GameStateNode:
    def __init__(self, red_frogs, blue_frogs, lily_pads,
                 isMax, color, name=None, depth=0, max_depth=2):
        self.red_frogs = set(red_frogs)
        self.blue_frogs = set(blue_frogs)
        self.lily_pads = set(lily_pads)
        self.isMax = isMax            
        self.color = color            
        self.name = name              
        self.depth = depth
        self.max_depth = max_depth


    def isLeaf(self):
        return self.depth >= self.max_depth

    def evaluate(self):
        # simple heuristic: difference in forward progress
        red_progress = sum(f.r for f in self.red_frogs)
        blue_progress = sum(7 - f.r for f in self.blue_frogs)
        if self.color == PlayerColor.RED:
            return red_progress - blue_progress
        else:
            return blue_progress - red_progress

    def children(self):
        children = []
        active = self.color if self.isMax else (
            PlayerColor.BLUE if self.color == PlayerColor.RED else PlayerColor.RED
        )
        frogs = self.red_frogs if active == PlayerColor.RED else self.blue_frogs
        opponent = self.blue_frogs if active == PlayerColor.RED else self.red_frogs

        # allowed directions
        if active == PlayerColor.RED:
            allowed_dirs = {Direction.Right, Direction.Left,
                            Direction.Down, Direction.DownLeft, Direction.DownRight}
        else:
            allowed_dirs = {Direction.Right, Direction.Left,
                            Direction.Up, Direction.UpLeft, Direction.UpRight}
        all_frogs = self.red_frogs | self.blue_frogs

        # 1-step moves
        for frog in frogs:
            for d in allowed_dirs:
                dest = apply_direction(frog, d)
                if dest and dest in self.lily_pads and dest not in all_frogs:
                    action = MoveAction(frog, [d])
                    new_red = set(self.red_frogs)
                    new_blue = set(self.blue_frogs)
                    new_lilies = set(self.lily_pads)
                    # remove lily pad at start
                    new_lilies.discard(frog)
                    # move frog
                    if active == PlayerColor.RED:
                        new_red.discard(frog); new_red.add(dest)
                    else:
                        new_blue.discard(frog); new_blue.add(dest)
                    children.append(
                        GameStateNode(new_red, new_blue, new_lilies,
                                      not self.isMax, self.color,
                                      name=action, depth=self.depth+1,
                                      max_depth=self.max_depth)
                    )

        # jumps
        jumps = []
        for frog in frogs:
            paths = find_jumps(frog, frog, allowed_dirs, all_frogs, self.lily_pads, {frog}, [])
            for path in paths:
                # compute landing
                current = frog
                for d in path:
                    over = apply_direction(current, d)
                    current = apply_direction(over, d)

                action = MoveAction(frog, path)
                new_red = set(self.red_frogs)
                new_blue = set(self.blue_frogs)
                new_lilies = set(self.lily_pads)
                new_lilies.discard(frog)
                if active == PlayerColor.RED:
                    new_red.discard(frog); new_red.add(current)
                else:
                    new_blue.discard(frog); new_blue.add(current)

                children.append(
                    GameStateNode(new_red, new_blue, new_lilies,
                                  not self.isMax, self.color,
                                  name=action, depth=self.depth+1,
                                  max_depth=self.max_depth)
                )

        # grow
        action = GrowAction()
        new_red = set(self.red_frogs)
        new_blue = set(self.blue_frogs)
        new_lilies = set(self.lily_pads)
        frogs_to_grow = new_red if active == PlayerColor.RED else new_blue
        for f in frogs_to_grow:
            for adj in adjacent_coords(f):
                new_lilies.add(adj)
        children.append(
            GameStateNode(new_red, new_blue, new_lilies,
                          not self.isMax, self.color,
                          name=action, depth=self.depth+1,
                          max_depth=self.max_depth)
        )

        return children

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self.red_frogs  = {Coord(0, i) for i in range(1,7)}
        self.blue_frogs = {Coord(7, i) for i in range(1,7)}
        self.lily_pads  = {Coord(0,0), Coord(0,7), *{Coord(1,c) for c in range(1,7)},
                           *{Coord(6,c) for c in range(1,7)}, Coord(7,0), Coord(7,7)}

    def action(self, **referee: dict) -> Action:
        # build root node and run αβ-minimax
        MAX_DEPTH = 2
        root = GameStateNode(self.red_frogs, self.blue_frogs, self.lily_pads,
                              isMax=True, color=self._color,
                              name=None, depth=0, max_depth=MAX_DEPTH)
        _, best = minimax_alpha_beta(root, float('-inf'), float('inf'))
        if best:
            best_move = best[0]   # the MoveAction/GrowAction stored in node.name
            return best_move
        # fallback
        return GrowAction()

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

# The code below is taken wholesale from 
# Artificial Intelligence: Foundations of Computational Agents https://artint.info
# Copyright 2017-2024 David L. Poole and Alan K. Mackworth
# This work is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 4.0 International License.
# See: https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en

def minimax_alpha_beta(node, alpha, beta, depth=0):
    best=None      # only used if it will be pruned
    if node.isLeaf():
        return node.evaluate(),None
    elif node.isMax:
        for C in node.children():
            score,path = minimax_alpha_beta(C,alpha,beta,depth+1)
            if score >= beta:    # beta pruning
                return score, None 
            if score > alpha:
                alpha = score
                best = C.name, path
        return alpha,best
    else:
        for C in node.children():
            score,path = minimax_alpha_beta(C,alpha,beta,depth+1)
            if score <= alpha:     # alpha pruning
                return score, None
            if score < beta:
                beta=score
                best = C.name,path
        return beta,best
