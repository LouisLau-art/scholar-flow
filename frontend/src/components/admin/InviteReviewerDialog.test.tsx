import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { InviteReviewerDialog } from '@/components/admin/InviteReviewerDialog';

describe('InviteReviewerDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
  };

  it('renders nothing when closed', () => {
    render(<InviteReviewerDialog {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('Invite New Reviewer')).not.toBeInTheDocument();
  });

  it('renders correctly when open', () => {
    render(<InviteReviewerDialog {...defaultProps} />);
    expect(screen.getByText('Invite New Reviewer')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('reviewer@example.edu')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Dr. Jane Doe')).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(<InviteReviewerDialog {...defaultProps} />);
    
    // Attempt to submit without filling fields
    fireEvent.click(screen.getByText('Send Invite'));
    
    // Note: The browser validation might intercept this, but our code also checks
    // However, since we use `required` attribute on inputs, the form submit might not trigger if not handled by jsdom/testing-library fully.
    // Let's rely on our manual validation logic in handleSubmit: if (!email || !fullName)
    
    // We need to bypass HTML5 validation or fill one field only to trigger our React validation logic if any
    // Actually, handleSubmit has: if (!email || !fullName) setError('Please fill in all fields.')
    
    // Let's prevent default HTML validation for the test or just trust our handler
    // Ideally we fill empty strings explicitly if needed, but they are empty by default.
    
    // Mock preventDefault to allow the handler to run despite invalid HTML
    const form = screen.getByRole('button', { name: /Send Invite/i }).closest('form');
    fireEvent.submit(form!);

    expect(await screen.findByText('Please fill in all fields.')).toBeInTheDocument();
  });

  it('submits form with valid data', async () => {
    render(<InviteReviewerDialog {...defaultProps} />);
    
    fireEvent.change(screen.getByPlaceholderText('reviewer@example.edu'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Dr. Jane Doe'), { target: { value: 'John Doe' } });
    
    fireEvent.click(screen.getByText('Send Invite'));

    await waitFor(() => {
      expect(defaultProps.onConfirm).toHaveBeenCalledWith('test@example.com', 'John Doe');
    });
  });

  it('handles submission error', async () => {
    const onConfirmError = vi.fn().mockRejectedValue(new Error('Invite failed'));
    render(<InviteReviewerDialog {...defaultProps} onConfirm={onConfirmError} />);
    
    fireEvent.change(screen.getByPlaceholderText('reviewer@example.edu'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Dr. Jane Doe'), { target: { value: 'John Doe' } });
    
    fireEvent.click(screen.getByText('Send Invite'));

    expect(await screen.findByText('Invite failed')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(<InviteReviewerDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('Cancel'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onClose when close icon is clicked', () => {
    render(<InviteReviewerDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('✕'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
