<?php

declare(strict_types=1);

namespace App;

use Symfony\Bundle\FrameworkBundle\Kernel\MicroKernelTrait;
use Symfony\Component\HttpKernel\Kernel as BaseKernel;

final class Kernel extends BaseKernel
{
    use MicroKernelTrait;

    public function getCacheDir(): string
    {
        $instance = (string) (getenv('EZSCORE_INSTANCE') ?: '');
        if (!in_array($instance, ['online', 'local'], true)) {
            return parent::getCacheDir();
        }

        return $this->getProjectDir().'/var/cache/'.$instance.'/'.$this->environment;
    }

    public function getLogDir(): string
    {
        $instance = (string) (getenv('EZSCORE_INSTANCE') ?: '');
        if (!in_array($instance, ['online', 'local'], true)) {
            return parent::getLogDir();
        }

        return $this->getProjectDir().'/var/log/'.$instance;
    }
}
