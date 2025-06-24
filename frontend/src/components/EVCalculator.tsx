import React, { useState } from "react";
import {
  Box,
  Paper,
  TextField,
  Typography,
  Grid,
  Button,
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
}

const EVCalculator: React.FC = () => {
  const [betAmount, setBetAmount] = useState<string>("");
  const [betOdds, setBetOdds] = useState<string>("");
  const [trueOdds, setTrueOdds] = useState<string>("");
  const [oddsFormat, setOddsFormat] = useState<string>("american");
  const [result, setResult] = useState<EVResult | null>(null);

  const handleOddsFormatChange = (event: SelectChangeEvent) => {
    setOddsFormat(event.target.value);
    // Reset results when format changes
    setResult(null);
  };

  const calculateExpectedValue = () => {
    try {
      const betAmountNum = parseFloat(betAmount);
      const betOddsNum = parseFloat(betOdds);
      const trueOddsNum = parseFloat(trueOdds);

      if (isNaN(betAmountNum) || isNaN(betOddsNum) || isNaN(trueOddsNum)) {
        throw new Error("Please enter valid numbers");
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

      setResult({
        ev,
        decimalOdds: trueDecimalOdds,
        impliedProbability,
      });
    } catch (error) {
      console.error("Error calculating EV:", error);
      setResult(null);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
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
              onChange={handleOddsFormatChange}
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
        <Grid item xs={12}>
          <Button
            fullWidth
            variant="contained"
            onClick={calculateExpectedValue}
            disabled={!betAmount || !betOdds || !trueOdds}
          >
            Calculate EV
          </Button>
        </Grid>
        {result && (
          <Grid item xs={12}>
            <Box sx={{ mt: 2, p: 2, bgcolor: "background.paper", borderRadius: 1 }}>
              <Typography variant="subtitle1" gutterBottom>
                Results:
              </Typography>
              <Typography>
                Expected Value: ${result.ev.toFixed(2)}
              </Typography>
              <Typography>
                Decimal Odds: {result.decimalOdds.toFixed(3)}
              </Typography>
              <Typography>
                Implied Probability: {result.impliedProbability.toFixed(2)}%
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default EVCalculator;
