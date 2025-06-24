import React, { useState, useEffect } from "react";
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Divider,
  Badge,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@mui/material";
import {
  PlayArrow,
  Stop,
  Refresh,
  FilterList,
  TrendingUp,
  TrendingDown,
  SportsBasketball,
  SportsSoccer,
  SportsFootball,
  SportsBaseball,
  SportsHockey,
  Casino,
} from "@mui/icons-material";

interface PTOProp {
  prop: {
    sport: string;
    teams: string[];
    propDesc: string;
    betType: string;
    odds: string;
    width: string;
    gameTime: string;
    fairValue: string;
    ev: string;
    timestamp: string;
  };
  created_at: string;
  updated_at: string;
}

interface PTOData {
  props: PTOProp[];
  total_count: number;
  last_update: string;
}

interface ScraperStatus {
  is_running: boolean;
  total_props: number;
  last_refresh: number;
  refresh_interval: number;
}

const PropBuilder: React.FC = () => {
  const [ptoData, setPtoData] = useState<PTOData | null>(null);
  const [scraperStatus, setScraperStatus] = useState<ScraperStatus | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [minEvFilter, setMinEvFilter] = useState<number>(3.0);
  const [sportFilter, setSportFilter] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showOnlyPositiveEv, setShowOnlyPositiveEv] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const [manualRefresh, setManualRefresh] = useState(false);

  const API_BASE = "http://localhost:5001";

  const getSportEmoji = (sport: string): React.ReactElement => {
    const sportLower = sport.toLowerCase();
    if (sportLower.includes("nba") || sportLower.includes("wnba"))
      return <SportsBasketball />;
    if (sportLower.includes("mlb")) return <SportsBaseball />;
    if (sportLower.includes("nfl")) return <SportsFootball />;
    if (sportLower.includes("nhl")) return <SportsHockey />;
    if (
      sportLower.includes("soccer") ||
      sportLower.includes("futbol") ||
      sportLower.includes("football")
    )
      return <SportsSoccer />;
    return <Casino />;
  };

  const getEvColor = (ev: string): string => {
    try {
      const evValue = parseFloat(ev.replace("%", ""));
      if (evValue > 5) return "#4caf50"; // Green for high EV
      if (evValue > 0) return "#8bc34a"; // Light green for positive EV
      if (evValue > -5) return "#ff9800"; // Orange for slightly negative
      return "#f44336"; // Red for very negative
    } catch {
      return "#757575"; // Gray for invalid values
    }
  };

  const getEvTrend = (ev: string): React.ReactElement | null => {
    try {
      const evValue = parseFloat(ev.replace("%", ""));
      if (evValue > 0)
        return <TrendingUp sx={{ color: "#4caf50" }} />;
      if (evValue < 0)
        return <TrendingDown sx={{ color: "#f44336" }} />;
      return null;
    } catch {
      return null;
    }
  };

  const fetchPTOData = async (isManual = false) => {
    if (initialLoad || isManual) setLoading(true);
    setError(null);
    try {
      const endpoint = showOnlyPositiveEv
        ? `/pto/props/ev/${minEvFilter}`
        : "/pto/props";
      const response = await fetch(`${API_BASE}${endpoint}`);
      if (!response.ok) throw new Error("Failed to fetch PTO data");
      const data = await response.json();
      const safeProps = (data.data.props || []).filter((p: any, i: number) => {
        const valid = p && typeof p === 'object' && p.prop && p.prop.sport;
        if (!valid) {
          console.warn(`[PropBuilder] Skipping malformed prop at index ${i}:`, p);
        }
        return valid;
      });
      console.log('[PropBuilder] Filtered safeProps:', safeProps);
      setPtoData({ ...data.data, props: safeProps });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      if (initialLoad) setInitialLoad(false);
      setLoading(false);
      setManualRefresh(false);
    }
  };

  const fetchScraperStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/pto/scraper/status`);
      if (response.ok) {
        const data = await response.json();
        setScraperStatus(data.data);
      }
    } catch (err) {
      console.error("Failed to fetch scraper status:", err);
    }
  };

  const toggleScraper = async (start: boolean) => {
    try {
      const endpoint = start ? "/pto/scraper/start" : "/pto/scraper/stop";
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
      });
      if (response.ok) {
        await fetchScraperStatus();
        if (start) await fetchPTOData();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle scraper");
    }
  };

  useEffect(() => {
    fetchPTOData();
    fetchScraperStatus();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchPTOData();
        fetchScraperStatus();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  useEffect(() => {
    fetchPTOData();
  }, [minEvFilter, showOnlyPositiveEv]);

  const filteredProps =
    ptoData?.props.filter((prop) => {
      if (
        sportFilter !== "all" &&
        !prop.prop.sport.toLowerCase().includes(sportFilter.toLowerCase())
      ) {
        return false;
      }
      return true;
    }) || [];

  const sports =
    ptoData?.props.reduce((acc: string[], p) => {
      if (!acc.includes(p.prop.sport)) {
        acc.push(p.prop.sport);
      }
      return acc;
    }, []) || [];

  // Manual refresh handler
  const handleManualRefresh = () => {
    setManualRefresh(true);
    fetchPTOData(true);
  };

  return (
    <Paper
      sx={{ p: 2, height: "100%", display: "flex", flexDirection: "column" }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h6" gutterBottom>
          Prop Builder EV
        </Typography>
        <Box
          sx={{ display: "flex", gap: 1, alignItems: "center" }}
        >
          <Tooltip title={scraperStatus?.is_running ? "Stop Scraper" : "Start Scraper"}>
            <IconButton
              onClick={() => toggleScraper(!scraperStatus?.is_running)}
              color={scraperStatus?.is_running ? "error" : "success"}
              size="small"
            >
              {scraperStatus?.is_running ? <Stop /> : <PlayArrow />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Refresh Data">
            <IconButton
              onClick={handleManualRefresh}
              disabled={loading}
              size="small"
            >
              <Refresh />
            </IconButton>
          </Tooltip>
          <Badge
            badgeContent={ptoData?.total_count || 0}
            color="primary"
          >
            <FilterList />
          </Badge>
        </Box>
      </Box>

      {/* Compact Status and Controls */}
      <Box sx={{ mb: 1 }}>
        <Grid container spacing={1} alignItems="center">
          <Grid item xs={6} sm={3} md={2}>
            <TextField
              label="Min EV %"
              type="number"
              value={minEvFilter}
              onChange={(e) => setMinEvFilter(parseFloat(e.target.value) || 0)}
              size="small"
              fullWidth
            />
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <FormControl size="small" fullWidth>
              <InputLabel>Sport</InputLabel>
              <Select
                value={sportFilter}
                onChange={(e) => setSportFilter(e.target.value)}
                label="Sport"
              >
                <MenuItem value="all">All Sports</MenuItem>
                {sports.map((sport) => (
                  <MenuItem key={sport} value={sport}>
                    {sport}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={showOnlyPositiveEv}
                  onChange={(e) => setShowOnlyPositiveEv(e.target.checked)}
                  size="small"
                />
              }
              label="+EV Only"
            />
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  size="small"
                />
              }
              label="Auto Refresh"
            />
          </Grid>
        </Grid>
      </Box>

      {/* Compact Status Alert */}
      {scraperStatus && (
        <Alert
          severity={scraperStatus.is_running ? "success" : "warning"}
          sx={{ mb: 1, py: 0.5 }}
        >
          {scraperStatus.is_running ? "🟢 Running" : "🔴 Stopped"} | Props:{" "}
          {scraperStatus.total_props} | Last:{" "}
          {new Date(scraperStatus.last_refresh * 1000).toLocaleTimeString()}
        </Alert>
      )}

      {/* Error Display */}
      {error && (
        <Alert
          severity="error"
          sx={{ mb: 1, py: 0.5 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (initialLoad || manualRefresh) && (
        <Box
          sx={{ display: "flex", justifyContent: "center", p: 1 }}
        >
          <CircularProgress size={20} />
        </Box>
      )}

      {/* Props Display */}
      <Box
        sx={{
          flexGrow: 1,
          minHeight: "60vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        {scraperStatus?.is_running && filteredProps.length === 0 ? (
          <CircularProgress size={32} />
        ) : filteredProps.length > 0 ? (
          <TableContainer component={Paper} sx={{ background: '#181c24', borderRadius: 2, boxShadow: 3, mt: 2 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Sport</TableCell>
                  <TableCell>Teams</TableCell>
                  <TableCell>Game Time</TableCell>
                  <TableCell>Prop</TableCell>
                  <TableCell>Odds</TableCell>
                  <TableCell>Width</TableCell>
                  <TableCell>EV</TableCell>
                  <TableCell>Link</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredProps.map((prop, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>{getSportEmoji(prop.prop.sport || 'Unknown')}</TableCell>
                    <TableCell>{(prop.prop.teams && prop.prop.teams.length === 2) ? `${prop.prop.teams[0]} vs ${prop.prop.teams[1]}` : ''}</TableCell>
                    <TableCell>{prop.prop.gameTime}</TableCell>
                    <TableCell>{prop.prop.propDesc} | {prop.prop.betType}</TableCell>
                    <TableCell><b>{prop.prop.odds}</b></TableCell>
                    <TableCell sx={{ color: '#ffb300' }}>{prop.prop.width}</TableCell>
                    <TableCell sx={{ color: parseFloat((prop.prop.ev||'0').replace('%','')) >= 0 ? '#4caf50' : '#e53935' }}><b>{prop.prop.ev}</b></TableCell>
                    <TableCell><a href="https://betbck.com/Qubic/propbuilder.php" target="_blank" rel="noopener noreferrer">Bet</a></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : null}
      </Box>
    </Paper>
  );
};

export default PropBuilder;
