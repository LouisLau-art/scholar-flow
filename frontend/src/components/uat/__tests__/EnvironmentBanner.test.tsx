import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import EnvironmentBanner from '../EnvironmentBanner';

// Mock the env lib to control IS_STAGING
// Since IS_STAGING is a constant exported from a module, we might need to mock the module.
// However, EnvironmentBanner usually renders based on props or internal logic.
// If it reads IS_STAGING directly, we need to mock that.

// Assuming EnvironmentBanner might take a prop or we mock the module.
// Let's assume we mock the module for test stability.

vi.mock('@/lib/env', () => ({
  IS_STAGING: true,
}));

describe('EnvironmentBanner', () => {
  it('renders the staging banner when in staging environment', () => {
    render(<EnvironmentBanner />);
    
    // Check for the text
    const bannerText = screen.getByText('Current Environment: UAT Staging (Not for Production)');
    expect(bannerText).toBeInTheDocument();
    
    // Check style (fixed position) - optional but good for visual reqs
    // Note: verifying exact css classes is brittle, but we can check if it exists.
  });
});
