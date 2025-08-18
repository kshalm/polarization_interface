import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PolarizationControl from '../PolarizationControl';
import { polarizationAPI } from '../../services/api';

// Mock the API
jest.mock('../../services/api');

describe('PolarizationControl', () => {
  const mockOnStatusChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders component with title', () => {
    polarizationAPI.getPaths.mockResolvedValue({
      data: { success: true, data: { paths: ['1', '2', 'a_calib'] } }
    });

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    expect(screen.getByText('Polarization State')).toBeInTheDocument();
    expect(screen.getByLabelText('Select Polarization Path:')).toBeInTheDocument();
  });

  test('loads available paths on mount', async () => {
    const mockPaths = ['1', '2', 'a_calib', 'b_calib'];
    polarizationAPI.getPaths.mockResolvedValue({
      data: { success: true, data: { paths: mockPaths } }
    });

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    await waitFor(() => {
      expect(polarizationAPI.getPaths).toHaveBeenCalledTimes(1);
    });

    // Check that Bell Angles is first option, followed by paths
    const select = screen.getByLabelText('Select Polarization Path:');
    expect(select).toBeInTheDocument();
    
    // Wait for options to load
    await waitFor(() => {
      expect(screen.getByText('Bell Angles')).toBeInTheDocument();
      mockPaths.forEach(path => {
        expect(screen.getByText(path)).toBeInTheDocument();
      });
    });
  });

  test('handles set polarization for bell angles', async () => {
    polarizationAPI.getPaths.mockResolvedValue({
      data: { success: true, data: { paths: ['1', '2'] } }
    });
    polarizationAPI.setBellAngles.mockResolvedValue({
      data: { success: true, message: 'Bell angles set' }
    });

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    await waitFor(() => {
      expect(screen.getByText('Bell Angles')).toBeInTheDocument();
    });

    // Select Bell Angles (should be selected by default)
    const select = screen.getByLabelText('Select Polarization Path:');
    fireEvent.change(select, { target: { value: 'Bell Angles' } });

    // Click Set button
    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    await waitFor(() => {
      expect(polarizationAPI.setBellAngles).toHaveBeenCalledTimes(1);
      expect(mockOnStatusChange).toHaveBeenCalledWith('success', 'Polarization set to: Bell Angles');
    });
  });

  test('handles set polarization for regular path', async () => {
    polarizationAPI.getPaths.mockResolvedValue({
      data: { success: true, data: { paths: ['1', '2'] } }
    });
    polarizationAPI.setPolarization.mockResolvedValue({
      data: { success: true, message: 'Polarization set' }
    });

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    // Select path '1'
    const select = screen.getByLabelText('Select Polarization Path:');
    fireEvent.change(select, { target: { value: '1' } });

    // Click Set button
    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    await waitFor(() => {
      expect(polarizationAPI.setPolarization).toHaveBeenCalledWith('1');
      expect(mockOnStatusChange).toHaveBeenCalledWith('success', 'Polarization set to: 1');
    });
  });

  test('handles API error', async () => {
    polarizationAPI.getPaths.mockResolvedValue({
      data: { success: true, data: { paths: ['1'] } }
    });
    polarizationAPI.setPolarization.mockRejectedValue({
      response: { data: { detail: 'Invalid setting' } }
    });

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    const select = screen.getByLabelText('Select Polarization Path:');
    fireEvent.change(select, { target: { value: '1' } });

    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid setting')).toBeInTheDocument();
      expect(mockOnStatusChange).toHaveBeenCalledWith('error', 'Invalid setting');
    });
  });

  test('shows loading state during API call', async () => {
    polarizationAPI.getPaths.mockResolvedValue({
      data: { success: true, data: { paths: ['1'] } }
    });
    
    // Create a promise that we can control
    let resolvePromise;
    const promise = new Promise(resolve => {
      resolvePromise = resolve;
    });
    polarizationAPI.setPolarization.mockReturnValue(promise);

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    const select = screen.getByLabelText('Select Polarization Path:');
    fireEvent.change(select, { target: { value: '1' } });

    const setButton = screen.getByText('Set');
    fireEvent.click(setButton);

    // Check loading state
    expect(screen.getByText('Setting...')).toBeInTheDocument();
    expect(setButton).toBeDisabled();

    // Resolve the promise
    resolvePromise({ data: { success: true } });

    await waitFor(() => {
      expect(screen.getByText('Set')).toBeInTheDocument();
      expect(setButton).not.toBeDisabled();
    });
  });

  test('handles paths loading error', async () => {
    polarizationAPI.getPaths.mockRejectedValue(new Error('Network error'));

    render(<PolarizationControl onStatusChange={mockOnStatusChange} />);
    
    await waitFor(() => {
      expect(mockOnStatusChange).toHaveBeenCalledWith('error', 'Failed to load polarization paths');
    });
  });
});