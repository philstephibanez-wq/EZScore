<?php

declare(strict_types=1);

/**
 * Repair UTF-8 text that was accidentally decoded through DOS/OEM code pages
 * (typically CP850 / CP437) and then written back as UTF-8.
 *
 * Examples:
 *   R├®pertoire      -> Répertoire
 *   Fran├ºais        -> Français
 *   biblioth├¿que    -> bibliothèque
 *   dΓÇÖacc├¿s       -> d’accès
 */
function ezscoreBuildMojibakeMap(): array
{
    if (!function_exists('iconv')) {
        throw new RuntimeException('PHP iconv extension is required.');
    }

    $originalCharacters = [
        'é','è','ê','ë','à','â','ä','ù','û','ü','ô','ö','î','ï','ç',
        'É','È','Ê','Ë','À','Â','Ä','Ù','Û','Ü','Ô','Ö','Î','Ï','Ç',
        'œ','Œ','æ','Æ',
        '’','‘','“','”','«','»','…','–','—','·','°','€',
        ' ', // NBSP
    ];

    $map = [];

    foreach ($originalCharacters as $original) {
        foreach (['CP850', 'CP437'] as $codePage) {
            $broken = @iconv($codePage, 'UTF-8//IGNORE', $original);
            if (!is_string($broken) || $broken === '' || $broken === $original) {
                continue;
            }

            $map[$broken] = $original;
        }
    }

    // Longest broken tokens first so multi-byte mojibake sequences are repaired
    // before shorter fragments.
    uksort(
        $map,
        static fn (string $a, string $b): int => strlen($b) <=> strlen($a)
    );

    return $map;
}

function ezscoreRepairMojibake(string $content): string
{
    $map = ezscoreBuildMojibakeMap();

    // A few historical files may have passed through the bad conversion more
    // than once. Iterating is safe because correct UTF-8 strings do not match
    // the generated broken tokens.
    for ($pass = 0; $pass < 3; ++$pass) {
        $before = $content;
        $content = strtr($content, $map);

        if ($content === $before) {
            break;
        }
    }

    return $content;
}

function ezscoreContainsMojibake(string $content): bool
{
    foreach ([
        '├', '┬', 'ΓÇ', 'Γé', 'ÔÇ', 'â€™', 'â€œ', 'â€', 'Fran├',
        'R├', 'Cr├', 'biblioth├',
    ] as $marker) {
        if (str_contains($content, $marker)) {
            return true;
        }
    }

    return false;
}

function ezscoreRepairTranslationDirectory(string $projectDir): array
{
    $translationDir = $projectDir.DIRECTORY_SEPARATOR.'translations';

    if (!is_dir($translationDir)) {
        throw new RuntimeException('translations directory not found: '.$translationDir);
    }

    $backupDir = $projectDir
        .DIRECTORY_SEPARATOR.'var'
        .DIRECTORY_SEPARATOR.'backup'
        .DIRECTORY_SEPARATOR.'translations-r25_2-'.date('Ymd-His');

    if (!mkdir($backupDir, 0775, true) && !is_dir($backupDir)) {
        throw new RuntimeException('Unable to create translation backup directory.');
    }

    $changed = [];
    $unchanged = [];

    $files = glob($translationDir.DIRECTORY_SEPARATOR.'*.yaml') ?: [];

    foreach ($files as $path) {
        $name = basename($path);
        $content = file_get_contents($path);

        if (!is_string($content)) {
            throw new RuntimeException('Unable to read '.$path);
        }

        $repaired = ezscoreRepairMojibake($content);

        if ($repaired === $content) {
            $unchanged[] = $name;
            continue;
        }

        if (!copy($path, $backupDir.DIRECTORY_SEPARATOR.$name)) {
            throw new RuntimeException('Unable to back up '.$path);
        }

        if (file_put_contents($path, $repaired, LOCK_EX) === false) {
            throw new RuntimeException('Unable to write '.$path);
        }

        $changed[] = $name;
    }

    return [
        'backup_dir' => $backupDir,
        'changed' => $changed,
        'unchanged' => $unchanged,
    ];
}

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    $projectDir = dirname(__DIR__);

    if (in_array('--self-test', $argv, true)) {
        $samples = [
            'R├®pertoire' => 'Répertoire',
            'Fran├ºais' => 'Français',
            'biblioth├¿que' => 'bibliothèque',
            'dΓÇÖacc├¿s' => 'd’accès',
            'Cr├®er' => 'Créer',
            'Éditeur' => 'Éditeur',
        ];

        foreach ($samples as $input => $expected) {
            $actual = ezscoreRepairMojibake($input);
            if ($actual !== $expected) {
                fwrite(STDERR, sprintf(
                    "FAIL: %s => %s (expected %s)\n",
                    $input,
                    $actual,
                    $expected,
                ));
                exit(1);
            }
        }

        fwrite(STDOUT, "OK: translation encoding self-test passed.\n");
        exit(0);
    }

    $result = ezscoreRepairTranslationDirectory($projectDir);

    fwrite(STDOUT, "[OK] Backup: ".$result['backup_dir'].PHP_EOL);

    if ($result['changed'] === []) {
        fwrite(STDOUT, "[OK] No corrupted translation file detected.".PHP_EOL);
    } else {
        fwrite(STDOUT, "[OK] Repaired: ".implode(', ', $result['changed']).PHP_EOL);
    }

    $remaining = [];
    foreach (glob($projectDir.DIRECTORY_SEPARATOR.'translations'.DIRECTORY_SEPARATOR.'*.yaml') ?: [] as $path) {
        $content = (string) file_get_contents($path);
        if (ezscoreContainsMojibake($content)) {
            $remaining[] = basename($path);
        }
    }

    if ($remaining !== []) {
        fwrite(STDERR, '[ERROR] Suspicious encoding remains in: '.implode(', ', $remaining).PHP_EOL);
        exit(2);
    }

    fwrite(STDOUT, "[OK] No known mojibake marker remains in translations/*.yaml".PHP_EOL);
}
