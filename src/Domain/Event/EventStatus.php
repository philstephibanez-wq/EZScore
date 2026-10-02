<?php
declare(strict_types=1);

namespace App\Domain\Event;

enum EventStatus: string
{
    case Draft = 'draft';
    case Validated = 'validated';
    case Scheduled = 'scheduled';
    case Cancelled = 'cancelled';
    case Completed = 'completed';
}
