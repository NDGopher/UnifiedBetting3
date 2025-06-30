import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Paper,
  Typography,
  Box,
  Grid,
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
  SportsBasketball,
  SportsSoccer,
  SportsFootball,
  SportsBaseball,
  SportsHockey,
  Casino,
  Delete,
} from "@mui/icons-material";
import { useWebSocket } from '../hooks/useWebSocket';

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
    books: string[];
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
  const prevPropsRef = useRef<any[]>([]);
  const { lastMessage, isConnected } = useWebSocket('ws://localhost:5001/ws');
  const [hiddenProps, setHiddenProps] = useState<Set<string>>(new Set());
  const [showHidden, setShowHidden] = useState(false);

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

  const fetchPTOData = useCallback(async (isManual = false) => {
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
      setPtoData({ ...data.data, props: safeProps });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      if (initialLoad) setInitialLoad(false);
      setLoading(false);
      setManualRefresh(false);
    }
  }, [initialLoad, showOnlyPositiveEv, minEvFilter]);

  const fetchScraperStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/pto/scraper/status`);
      if (response.ok) {
        const data = await response.json();
        setScraperStatus(data.data);
      }
    } catch (err) {
      console.error("Failed to fetch scraper status:", err);
    }
  }, []);

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
  }, [fetchPTOData, fetchScraperStatus]);

  useEffect(() => {
    if (autoRefresh && !isConnected) {
      // Only poll if WebSocket is not connected
      const interval = setInterval(() => {
        fetchPTOData();
        fetchScraperStatus();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchPTOData, fetchScraperStatus, isConnected]);

  useEffect(() => {
    fetchPTOData();
  }, [minEvFilter, showOnlyPositiveEv, fetchPTOData]);

  useEffect(() => {
    if (ptoData && ptoData.props && ptoData.props.length > 0) {
      ptoData.props.forEach((p, idx) => {
        const prev = prevPropsRef.current[idx];
        if (prev && prev.prop) {
          if (
            p.prop.ev !== prev.prop.ev ||
            p.prop.width !== prev.prop.width
          ) {
            console.log(
              `[PropBuilder] EV/Width changed for ${p.prop.propDesc} (${p.prop.teams?.join(' vs ') || ''}):`,
              `EV: ${prev.prop.ev} → ${p.prop.ev}, Width: ${prev.prop.width} → ${p.prop.width}`
            );
          }
        }
      });
      prevPropsRef.current = ptoData.props;
    }
  }, [ptoData]);

  // WebSocket: update PTO data on new message
  useEffect(() => {
    if (lastMessage && lastMessage.data) {
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === 'pto_prop_update' && data.props) {
          // Replace the entire PTO prop list with the latest from backend
          setPtoData({
            props: data.props,
            total_count: data.total_count || 0,
            last_update: data.last_update || new Date().toISOString()
          });
        }
      } catch (e) {
        console.error('[PropBuilder] WebSocket message parse error:', e);
      }
    }
  }, [lastMessage]);

  const handleHideProp = (propId: string) => {
    setHiddenProps(prev => new Set(prev).add(propId));
  };

  const filteredProps = (ptoData?.props ?? []).filter((prop) => {
    const propId = prop.prop && prop.prop.propDesc ? prop.prop.propDesc + (prop.prop.teams?.join('-') || '') : '';
    if (!showHidden && hiddenProps.has(propId)) return false;
    if (
      sportFilter !== "all" &&
      !prop.prop.sport.toLowerCase().includes(sportFilter.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const sports = (ptoData?.props ?? []).reduce((acc: string[], p) => {
    if (!acc.includes(p.prop.sport)) {
      acc.push(p.prop.sport);
    }
    return acc;
  }, []);

  // Manual refresh handler
  const handleManualRefresh = () => {
    setManualRefresh(true);
    fetchPTOData(true);
  };

  // Book logo mapping
  const bookLogoMap: Record<string, string> = {
    Pinnacle: '/book_icons/pinnacle.png',
    PIN: '/book_icons/pinnacle.png',
    DraftKings: '/book_icons/draftkings.png',
    DK: '/book_icons/draftkings.png',
    Bet365: '/book_icons/bet365.png',
    '365': '/book_icons/bet365.png',
    MGM: '/book_icons/mgm.png',
    Bovada: '/book_icons/bovada.png',
    HardRock: '/book_icons/hardrock.png',
    Caesars: '/book_icons/caesars.png',
    FanDuel: '/book_icons/fanduel.png',
    BetRivers: '/book_icons/betrivers.png',
    Circa: '/book_icons/circa.png',
    // Add more as needed
  };

  const normalizeBook = (book: string) => {
    const map: Record<string, string> = {
      PIN: 'Pinnacle',
      DK: 'DraftKings',
      '365': 'Bet365',
      // ...add more as needed
    };
    return map[book] || book;
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
          <Grid item xs={6} sm={3} md={2}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <FormControlLabel
                control={<Switch checked={showHidden} onChange={e => setShowHidden(e.target.checked)} size="small" />}
                label="Show Hidden"
              />
            </Box>
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
          mt: 0,
          mb: 0,
          overflow: "hidden",
        }}
      >
        {scraperStatus?.is_running && filteredProps.length === 0 ? (
          <CircularProgress />
        ) : filteredProps.length > 0 ? (
          <Grid container spacing={2}>
            {filteredProps.map((propObj, idx) => {
              const prop = propObj.prop;
              const propId = prop.propDesc + (prop.teams?.join('-') || '');
              // Debug: log the full prop object and books field
              console.log('Full prop object:', propObj);
              console.log('prop.books:', (prop as any).books);
              return (
                <Grid item xs={12} md={6} lg={4} key={propId}>
                  <Paper sx={{ p: 2, borderRadius: 3, boxShadow: 4, mb: 2, background: '#181c24', position: 'relative' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      {getSportEmoji(prop.sport)}
                      <Typography variant="subtitle1" sx={{ ml: 1, fontWeight: 600 }}>{prop.teams?.join(' vs ')}</Typography>
                      <Typography variant="body2" sx={{ ml: 2, color: 'gray' }}>{prop.gameTime}</Typography>
                      <IconButton size="small" sx={{ ml: 'auto' }} onClick={() => handleHideProp(propId)}><Delete fontSize="small" /></IconButton>
                    </Box>
                    <Box sx={{ mb: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>{prop.propDesc}</Typography>
                      <Typography variant="body2" sx={{ color: 'lightgreen', fontWeight: 700 }}>{prop.odds}</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ color: 'cyan', fontWeight: 700 }}>EV: {prop.ev}</Typography>
                        {prop.fairValue && (
                          <Typography variant="body2" sx={{ color: 'gray', fontSize: '0.9em' }}>({prop.fairValue})</Typography>
                        )}
                      </Box>
                    </Box>
                    <Box sx={{ mt: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="body2" sx={{ mr: 1 }}>Width:</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{prop.width}</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                        {Array.isArray(prop.books) && prop.books.map(book => (
                          <Tooltip key={book} title={book}>
                            <img
                              src={bookLogoMap[normalizeBook(book)] || '/book_icons/pinnacle.png'}
                              alt={book}
                              style={{ width: 28, height: 28, marginRight: 4, borderRadius: 6, background: '#222' }}
                            />
                          </Tooltip>
                        ))}
                      </Box>
                    </Box>
                  </Paper>
                </Grid>
              );
            })}
          </Grid>
        ) : (
          <Typography variant="body2" sx={{ color: 'gray', textAlign: 'center', mt: 2 }}>
            No props found.
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export default PropBuilder;
