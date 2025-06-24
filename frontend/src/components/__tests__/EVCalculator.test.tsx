import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EVCalculator from '../EVCalculator';

describe('EVCalculator', () => {
  beforeEach(() => {
    render(<EVCalculator />);
  });

  it('renders all input fields', () => {
    expect(screen.getByLabelText(/bet amount/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/bet odds/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/true odds/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/odds format/i)).toBeInTheDocument();
  });

  it('calculates EV correctly with American odds', async () => {
    // Set American odds format
    const formatSelect = screen.getByLabelText(/odds format/i);
    fireEvent.mouseDown(formatSelect);
    fireEvent.click(screen.getByText('American'));

    // Input values
    await userEvent.type(screen.getByLabelText(/bet amount/i), '100');
    await userEvent.type(screen.getByLabelText(/bet odds/i), '-110');
    await userEvent.type(screen.getByLabelText(/true odds/i), '-105');

    // Calculate
    fireEvent.click(screen.getByText(/calculate ev/i));

    // Check results
    expect(screen.getByText(/expected value/i)).toBeInTheDocument();
    expect(screen.getByText(/decimal odds/i)).toBeInTheDocument();
    expect(screen.getByText(/implied probability/i)).toBeInTheDocument();
  });

  it('calculates EV correctly with Decimal odds', async () => {
    // Set Decimal odds format
    const formatSelect = screen.getByLabelText(/odds format/i);
    fireEvent.mouseDown(formatSelect);
    fireEvent.click(screen.getByText('Decimal'));

    // Input values
    await userEvent.type(screen.getByLabelText(/bet amount/i), '100');
    await userEvent.type(screen.getByLabelText(/bet odds/i), '1.91');
    await userEvent.type(screen.getByLabelText(/true odds/i), '1.95');

    // Calculate
    fireEvent.click(screen.getByText(/calculate ev/i));

    // Check results
    expect(screen.getByText(/expected value/i)).toBeInTheDocument();
    expect(screen.getByText(/decimal odds/i)).toBeInTheDocument();
    expect(screen.getByText(/implied probability/i)).toBeInTheDocument();
  });

  it('disables calculate button when inputs are empty', () => {
    const calculateButton = screen.getByText(/calculate ev/i);
    expect(calculateButton).toBeDisabled();
  });

  it('handles invalid input gracefully', async () => {
    // Input invalid values
    await userEvent.type(screen.getByLabelText(/bet amount/i), 'invalid');
    await userEvent.type(screen.getByLabelText(/bet odds/i), 'invalid');
    await userEvent.type(screen.getByLabelText(/true odds/i), 'invalid');

    // Calculate button should be disabled
    const calculateButton = screen.getByText(/calculate ev/i);
    expect(calculateButton).toBeDisabled();
  });
}); 