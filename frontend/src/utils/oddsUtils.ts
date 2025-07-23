/**
 * Converts American odds to decimal odds
 * @param americanOdds - American odds (e.g., -110, +150)
 * @returns Decimal odds
 */
export const americanToDecimal = (americanOdds: number): number => {
  if (americanOdds > 0) {
    return (americanOdds / 100) + 1;
  } else {
    return (100 / Math.abs(americanOdds)) + 1;
  }
};

/**
 * Calculates the expected value of a bet
 * @param betAmount - Amount to bet
 * @param betDecimalOdds - Decimal odds of the bet
 * @param trueDecimalOdds - True decimal odds (no-vig)
 * @returns Expected value in dollars
 */
export const calculateEV = (
  betAmount: number,
  betDecimalOdds: number,
  trueDecimalOdds: number
): number => {
  const winProbability = 1 / trueDecimalOdds;
  const winAmount = betAmount * (betDecimalOdds - 1);
  const lossAmount = -betAmount;
  
  return (winProbability * winAmount) + ((1 - winProbability) * lossAmount);
};

/**
 * Converts decimal odds to American odds
 * @param decimalOdds - Decimal odds
 * @returns American odds
 */
export const decimalToAmerican = (decimalOdds: number): number => {
  if (decimalOdds >= 2) {
    return (decimalOdds - 1) * 100;
  } else {
    return -100 / (decimalOdds - 1);
  }
};

/**
 * Calculates the implied probability from decimal odds
 * @param decimalOdds - Decimal odds
 * @returns Implied probability as a decimal (0-1)
 */
export const calculateImpliedProbability = (decimalOdds: number): number => {
  return 1 / decimalOdds;
}; 