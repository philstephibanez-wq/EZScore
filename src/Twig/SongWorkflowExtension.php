<?php

declare(strict_types=1);
namespace App\Twig;
use App\Domain\Song\Song;
use App\Service\SongWorkflowState;
use Twig\Extension\AbstractExtension;
use Twig\TwigFunction;
final class SongWorkflowExtension extends AbstractExtension
{
    public function __construct(private readonly SongWorkflowState $workflow) {}
    public function getFunctions(): array { return [new TwigFunction('song_workflow',[$this,'workflow'])]; }
    public function workflow(Song $song): array { return $this->workflow->forSong($song); }
}
