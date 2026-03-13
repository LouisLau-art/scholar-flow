import type { ComponentProps } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { EditorialActionsCard } from '@/app/(admin)/editor/manuscript/[id]/detail-sections'

function buildProps(overrides: Partial<ComponentProps<typeof EditorialActionsCard>> = {}): ComponentProps<typeof EditorialActionsCard> {
  return {
    manuscriptId: 'manuscript-1',
    isPostAcceptance: false,
    canAssignReviewersStage: false,
    canExitReviewStage: false,
    canOpenDecisionWorkspaceStage: false,
    canManageReviewers: false,
    viewerRoles: ['managing_editor'],
    canRecordFirstDecision: false,
    canSubmitFinalDecision: false,
    canOpenProductionWorkspace: false,
    statusLower: 'pre_check',
    preCheckStatus: null,
    finalPdfPath: null,
    invoice: null,
    showDirectStatusTransitions: false,
    canManualStatusTransition: false,
    nextStatuses: [],
    transitioning: null,
    currentAeId: '',
    onReviewerChanged: vi.fn(),
    onOpenReviewStageExitDialog: vi.fn(),
    onOpenDecisionWorkspace: vi.fn(),
    onOpenProductionWorkspace: vi.fn(),
    onReload: vi.fn(),
    onOpenTransitionDialog: vi.fn(),
    getTransitionActionLabel: (nextStatus: string) => nextStatus,
    onOpenAuthorEmailPreview: vi.fn(),
    ...overrides,
  }
}

describe('EditorialActionsCard author communication', () => {
  it('hides technical revision email action for academic precheck stage', () => {
    render(
      <EditorialActionsCard
        {...buildProps({
          statusLower: 'pre_check',
          preCheckStatus: 'academic',
        })}
      />
    )

    expect(screen.queryByRole('button', { name: /Send Technical Revision Email/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Send Formal Revision Request Email/i })).not.toBeInTheDocument()
  })

  it('shows technical revision email action for intake / technical precheck flows', () => {
    render(
      <EditorialActionsCard
        {...buildProps({
          statusLower: 'pre_check',
          preCheckStatus: 'technical',
        })}
      />
    )

    expect(screen.getByRole('button', { name: /Send Technical Revision Email/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Send Formal Revision Request Email/i })).not.toBeInTheDocument()
  })

  it('does not show formal revision request email before manuscript enters revision stage', () => {
    render(
      <EditorialActionsCard
        {...buildProps({
          statusLower: 'under_review',
          canAssignReviewersStage: true,
        })}
      />
    )

    expect(screen.queryByRole('button', { name: /Send Technical Revision Email/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Send Formal Revision Request Email/i })).not.toBeInTheDocument()
  })

  it('shows formal revision request email action only after manuscript enters revision stage', () => {
    render(
      <EditorialActionsCard
        {...buildProps({
          statusLower: 'major_revision',
        })}
      />
    )

    expect(screen.getByRole('button', { name: /Send Formal Revision Request Email/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Send Technical Revision Email/i })).not.toBeInTheDocument()
  })
})
