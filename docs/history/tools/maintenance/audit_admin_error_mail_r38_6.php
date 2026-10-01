<?php
declare(strict_types=1);
$root = realpath($argv[1] ?? dirname(__DIR__));
if ($root === false) { fwrite(STDERR, "Repository not found\n"); exit(2); }
$expected = strtolower(trim($argv[2] ?? 'xpertdev@hotmail.com'));
$dirs = ['src','config','worker_app','scripts'];
$extensions = ['php','yaml','yml','py','pyw','ps1','env','js'];
$hits = [];
foreach ($dirs as $dir) {
    $base = $root.DIRECTORY_SEPARATOR.$dir;
    if (!is_dir($base)) continue;
    $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base, FilesystemIterator::SKIP_DOTS));
    foreach ($it as $file) {
        if (!$file->isFile()) continue;
        $ext = strtolower(pathinfo($file->getFilename(), PATHINFO_EXTENSION));
        if (!in_array($ext, $extensions, true) && !str_starts_with($file->getFilename(), '.env')) continue;
        $text = @file_get_contents($file->getPathname());
        if (!is_string($text)) continue;
        $lines = preg_split('/\R/', $text) ?: [];
        foreach ($lines as $i => $line) {
            if (!preg_match('/(?:error|admin|recipient|->to\s*\(|addTo\s*\(|@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/i', $line)) continue;
            if (preg_match('/(?:password|secret|token|dsn)/i', $line)) continue;
            $relative = str_replace('\\', '/', substr($file->getPathname(), strlen($root)+1));
            $hits[] = sprintf('%s:%d: %s', $relative, $i+1, trim($line));
        }
    }
}
echo "ADMIN_ERROR_MAIL_RUNTIME_AUDIT\n";
echo "Expected admin: {$expected}\n";
foreach ($hits as $hit) echo $hit, PHP_EOL;
echo "AUDIT_HITS=", count($hits), PHP_EOL;
