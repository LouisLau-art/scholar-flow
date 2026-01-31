import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FeedbackWidget from '../FeedbackWidget';

// Mock fetch
global.fetch = vi.fn();

describe('FeedbackWidget', () => {
  it('renders the floating button initially', () => {
    render(<FeedbackWidget />);
    const button = screen.getByRole('button', { name: /report issue/i });
    expect(button).toBeInTheDocument();
  });

  it('opens dialog when clicked', () => {
    render(<FeedbackWidget />);
    const button = screen.getByRole('button', { name: /report issue/i });
    fireEvent.click(button);
    
    expect(screen.getByText('Report an Issue')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/describe the issue/i)).toBeInTheDocument();
  });

  it('submits feedback', async () => {
    render(<FeedbackWidget />);
    
    // Open
    fireEvent.click(screen.getByRole('button', { name: /report issue/i }));
    
    // Fill
    fireEvent.change(screen.getByPlaceholderText(/describe the issue/i), { target: { value: 'Test issue description' } });
    
    // Submit
    const submitBtn = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitBtn);
    
    // Assert fetch call
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/system/feedback', expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('Test issue description')
    }));
  });
});
