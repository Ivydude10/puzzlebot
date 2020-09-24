-- Get leaderboard
SELECT teamsolves.teamname AS teamname, MAX(teamsolves.last_solvetime) AS last_solvetime, COALESCE(SUM(puzzles.points), 0) AS total_points FROM
    (SELECT teams.id AS teamid, teams.teamname AS teamname, MAX(solves.solvetime) AS last_solvetime, solves.puzzleid as puzzleid, teams.huntid AS huntid FROM puzzledb.puzzlehunt_teams teams
    LEFT JOIN puzzledb.puzzlehunt_solves solves
        ON solves.teamid = teams.id AND solves.huntid = teams.huntid
        GROUP BY teams.id, solves.puzzleid) teamsolves
LEFT JOIN puzzledb.puzzlehunt_puzzles puzzles
    ON teamsolves.puzzleid = puzzles.puzzleid AND teamsolves.huntid = puzzles.huntid
    GROUP BY teamsolves.teamid, teamsolves.teamname
    ORDER BY total_points DESC, last_solvetime ASC;

