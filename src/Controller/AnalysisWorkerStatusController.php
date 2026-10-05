<?php

declare(strict_types=1);

namespace App\Controller;

use App\Service\AnalysisCapabilityState;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\Routing\Attribute\Route;

final class AnalysisWorkerStatusController extends AbstractController
{
    #[Route('/analysis/worker/status', name: 'app_analysis_worker_status', methods: ['GET'])]
    public function __invoke(AnalysisCapabilityState $state): JsonResponse
    {
        $this->denyAccessUnlessGranted('ROLE_EDITOR');

        return $this->json($state->publicStatus());
    }
}
