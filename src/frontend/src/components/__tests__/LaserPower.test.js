import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LaserPower from '../LaserPower';
import { polarizationAPI } from '../../services/api';

// Mock the API
jest.mock('../../services/api');

describe('LaserPower', () => {
  const mockOnStatusChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders component with title and input', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    expect(screen.getByText('Set Laser Power')).toBeInTheDocument();
    expect(screen.getByLabelText('Power Level (0.0 - 1.0):')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter power (e.g., 0.5)')).toBeInTheDocument();
  });

  test('accepts valid power input', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '0.5' } });
    
    expect(input.value).toBe('0.5');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  test('validates power input range - too high', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '1.5' } });
    
    expect(screen.getByText('Power must be between 0.0 and 1.0')).toBeInTheDocument();
  });

  test('validates power input range - too low', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '-0.1' } });
    
    expect(screen.getByText('Power must be between 0.0 and 1.0')).toBeInTheDocument();
  });

  test('validates non-numeric input', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: 'invalid' } });
    
    expect(screen.getByText('Power must be a valid number')).toBeInTheDocument();
  });

  test('successfully sets power', async () => {
    polarizationAPI.setPower.mockResolvedValue({
      data: { success: true, message: 'Power set' }
    });

    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '0.5' } });

    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    await waitFor(() => {
      expect(polarizationAPI.setPower).toHaveBeenCalledWith(0.5);
      expect(mockOnStatusChange).toHaveBeenCalledWith('success', 'Laser power set to 0.5');
    });
  });

  test('handles API error', async () => {
    polarizationAPI.setPower.mockRejectedValue({
      response: { data: { detail: 'Power setting failed' } }
    });

    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '0.5' } });

    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    await waitFor(() => {
      expect(screen.getByText('Power setting failed')).toBeInTheDocument();
      expect(mockOnStatusChange).toHaveBeenCalledWith('error', 'Power setting failed');
    });
  });

  test('handles Enter key press', async () => {
    polarizationAPI.setPower.mockResolvedValue({
      data: { success: true, message: 'Power set' }
    });

    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '0.3' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(polarizationAPI.setPower).toHaveBeenCalledWith(0.3);
    });
  });

  test('disables button when input is invalid', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    const setButton = screen.getByText('Set');

    // Initially disabled (no input)
    expect(setButton).toBeDisabled();

    // Still disabled with invalid input
    fireEvent.change(input, { target: { value: '1.5' } });
    expect(setButton).toBeDisabled();

    // Enabled with valid input
    fireEvent.change(input, { target: { value: '0.5' } });
    expect(setButton).not.toBeDisabled();
  });

  test('shows loading state during API call', async () => {
    // Create a promise that we can control
    let resolvePromise;
    const promise = new Promise(resolve => {
      resolvePromise = resolve;
    });
    polarizationAPI.setPower.mockReturnValue(promise);

    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    fireEvent.change(input, { target: { value: '0.5' } });

    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    // Check loading state
    expect(screen.getByText('Setting...')).toBeInTheDocument();
    expect(setButton).toBeDisabled();
    expect(input).toBeDisabled();

    // Resolve the promise
    resolvePromise({ data: { success: true } });

    await waitFor(() => {
      expect(screen.getByText('Set')).toBeInTheDocument();
      expect(setButton).not.toBeDisabled();
      expect(input).not.toBeDisabled();
    });
  });

  test('validates boundary values', () => {
    render(<LaserPower onStatusChange={mockOnStatusChange} />);
    
    const input = screen.getByLabelText('Power Level (0.0 - 1.0):');
    const setButton = screen.getByText('Set');

    // Test 0.0 (valid)
    fireEvent.change(input, { target: { value: '0.0' } });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(setButton).not.toBeDisabled();

    // Test 1.0 (valid)
    fireEvent.change(input, { target: { value: '1.0' } });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(setButton).not.toBeDisabled();
  });
});