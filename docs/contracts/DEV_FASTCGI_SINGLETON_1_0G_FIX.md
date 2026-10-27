# 1.0g — correction variable réservée PowerShell

Le premier gestionnaire 1.0f utilisait `$pid` ; PowerShell réserve `$PID` sans distinction de casse. Toute la variable locale est renommée `$storedPid`. Le test contractuel interdit sa réintroduction. Aucune action sur les services actifs ou Caddy ; valider la syntaxe sur MAIN avant tout start/stop.
