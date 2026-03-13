import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProductionWorkspacePanel } from '@/components/editor/production/ProductionWorkspacePanel'

// Mock dependencies
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@/services/editorApi', () => ({ EditorApi: {} }))

describe('ProductionWorkspacePanel', () => {
  it('renders SOP assignments and stage', () => {
    const mockContext: any = {
      manuscript: { id: 'm1', title: 'Test', author_id: 'a1' },
      active_cycle: {
        id: 'c1',
        cycle_no: 1,
        status: 'draft',
        stage: 'typesetting',
        typesetter_id: 'u1',
        coordinator_ae_id: 'u2',
        artifacts: []
      },
      cycle_history: [],
      permissions: { can_manage_editors: true }
    }
    
    render(<ProductionWorkspacePanel manuscriptId="m1" context={mockContext} staff={[{id:'u1', name:'User 1'}, {id:'u2', name:'User 2'}]} onReload={async () => {}} />)
    
    expect(screen.getByText('typesetting')).toBeDefined()
    expect(screen.getAllByText(/Assignments/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Upload Artifact/i).length).toBeGreaterThan(0)
  })

  it('uses neutral SOP copy when creating a cycle', () => {
    const mockContext: any = {
      manuscript: { id: 'm1', title: 'Test', author_id: 'a1' },
      active_cycle: null,
      cycle_history: [],
      permissions: { can_create_cycle: true, can_manage_editors: true },
    }

    render(
      <ProductionWorkspacePanel
        manuscriptId="m1"
        context={mockContext}
        staff={[{ id: 'u1', name: 'User 1', roles: ['production_editor'] }]}
        onReload={async () => {}}
      />
    )

    expect(screen.getByText('Initial Assignee')).toBeInTheDocument()
    expect(screen.queryByText('Layout Editor')).not.toBeInTheDocument()
  })

  it('does not expose legacy galley copy in the active cycle actions', () => {
    const mockContext: any = {
      manuscript: { id: 'm1', title: 'Test', author_id: 'a1' },
      active_cycle: {
        id: 'c1',
        cycle_no: 1,
        status: 'draft',
        stage: 'typesetting',
        galley_path: 'production/c1/galley.pdf',
        artifacts: [],
      },
      cycle_history: [],
      permissions: { can_manage_editors: true },
    }

    render(
      <ProductionWorkspacePanel
        manuscriptId="m1"
        context={mockContext}
        staff={[{ id: 'u1', name: 'User 1', roles: ['production_editor'] }]}
        onReload={async () => {}}
      />
    )

    expect(screen.getByRole('button', { name: 'Open Current Proof PDF' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Legacy/i })).not.toBeInTheDocument()
  })
})
