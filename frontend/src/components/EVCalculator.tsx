import React, { useState, useEffect } from "react";
import {
  Box,
  Paper,
  TextField,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from "@mui/material";
import { americanToDecimal, calculateEV } from "../utils/oddsUtils";

interface EVResult {
  ev: number;
  decimalOdds: number;
  impliedProbability: number;
  evPercent: number;
}

const EVCalculator: React.FC = () => {
  const [betAmount, setBetAmount] = useState<string>("");
  const [betOdds, setBetOdds] = useState<string>("");
  const [trueOdds, setTrueOdds] = useState<string>("");
  const [oddsFormat, setOddsFormat] = useState<string>("american");
  const [result, setResult] = useState<EVResult | null>(null);

  useEffect(() => {
    // Auto-calculate EV as inputs change
    try {
      const betAmountNum = parseFloat(betAmount);
      const betOddsNum = parseFloat(betOdds);
      const trueOddsNum = parseFloat(trueOdds);
      if (
        isNaN(betAmountNum) ||
        isNaN(betOddsNum) ||
        isNaN(trueOddsNum) ||
        betAmount === "" ||
        betOdds === "" ||
        trueOdds === ""
      ) {
        setResult(null);
        return;
      }
      let betDecimalOdds: number;
      let trueDecimalOdds: number;
      if (oddsFormat === "american") {
        betDecimalOdds = americanToDecimal(betOddsNum);
        trueDecimalOdds = americanToDecimal(trueOddsNum);
      } else {
        betDecimalOdds = betOddsNum;
        trueDecimalOdds = trueOddsNum;
      }
      const ev = calculateEV(betAmountNum, betDecimalOdds, trueDecimalOdds);
      const impliedProbability = (1 / trueDecimalOdds) * 100;
      const evPercent = ((betDecimalOdds / trueDecimalOdds) - 1) * 100;
      setResult({
        ev,
        decimalOdds: trueDecimalOdds,
        impliedProbability,
        evPercent,
      });
    } catch (error) {
      setResult(null);
    }
  }, [betAmount, betOdds, trueOdds, oddsFormat]);

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, mb: 2 }}>
      <Paper sx={{ p: 4, minWidth: 340, maxWidth: 400, width: '100%', textAlign: 'center', borderRadius: 3, boxShadow: 4 }}>
        <Typography variant="h6" gutterBottom>
          EV Calculator
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Odds Format</InputLabel>
              <Select
                value={oddsFormat}
                label="Odds Format"
                onChange={(e: SelectChangeEvent) => setOddsFormat(e.target.value)}
              >
                <MenuItem value="american">American</MenuItem>
                <MenuItem value="decimal">Decimal</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Bet Amount"
              type="number"
              value={betAmount}
              onChange={(e) => setBetAmount(e.target.value)}
              InputProps={{
                startAdornment: <Typography>$</Typography>,
              }}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Bet Odds"
              type="number"
              value={betOdds}
              onChange={(e) => setBetOdds(e.target.value)}
              InputProps={{
                startAdornment: oddsFormat === "american" && (
                  <Typography>{parseFloat(betOdds) > 0 ? "+" : ""}</Typography>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="True Odds"
              type="number"
              value={trueOdds}
              onChange={(e) => setTrueOdds(e.target.value)}
              InputProps={{
                startAdornment: oddsFormat === "american" && (
                  <Typography>{parseFloat(trueOdds) > 0 ? "+" : ""}</Typography>
                ),
              }}
            />
          </Grid>
          {result && (
            <Grid item xs={12}>
              <Box sx={{ mt: 2, p: 2, bgcolor: "background.paper", borderRadius: 1 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Results:
                </Typography>
                <Typography>
                  EV %: <b>{result.evPercent.toFixed(2)}%</b>
                </Typography>
                <Typography>
                  Expected Return: <b>${result.ev.toFixed(2)}</b>
                </Typography>
                <Typography>
                  Implied Probability: {result.impliedProbability.toFixed(2)}%
                </Typography>
              </Box>
            </Grid>
          )}
        </Grid>
      </Paper>
    </Box>
  );
};

export default EVCalculator;
