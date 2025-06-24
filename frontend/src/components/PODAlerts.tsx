import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Grid,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import StarIcon from '@mui/icons-material/Star';

interface Market {
  market: string;
  selection: string;
  line: string;
  pinnacle_nvp: string;
  betbck_odds: string;
  ev: string;
}

interface EventData {
  title: string;
  meta_info: string;
  last_update: number;
  alert_description: string;
  alert_meta: string;
  markets: Market[];
  alert_arrival_timestamp: number;
  start_time?: string;
  old_odds?: string;
  new_odds?: string;
}

const POLL_INTERVAL = 3000; // 3 seconds, matches old realtime.js
const AUTO_DISMISS_MS = 5 * 60 * 1000; // 5 minutes
const MAX_RETRIES = 3; // Maximum number of retries before showing error

const PODAlerts: React.FC = () => {
  const [events, setEvents] = useState<{ [eventId: string]: EventData }>({});
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [modalMarket, setModalMarket] = useState<null | { event: EventData; market: Market }>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [retryCount, setRetryCount] = useState(0);
  const [showOnlyEV, setShowOnlyEV] = useState(false);

  const fetchEvents = useCallback(async () => {
    try {
      console.log("[DEBUG] PODAlerts: Starting fetchEvents");
      setError(null);
      const res = await fetch('http://localhost:5001/get_active_events_data');
      console.log("[DEBUG] PODAlerts: Response status:", res.status);
      console.log("[DEBUG] PODAlerts: Response ok:", res.ok);
      
      if (res.ok) {
        const data = await res.json() as { [eventId: string]: EventData };
        console.log("[DEBUG] PODAlerts: Received data:", data);
        console.log("[DEBUG] PODAlerts: Data type:", typeof data);
        console.log("[DEBUG] PODAlerts: Data keys:", Object.keys(data));
        console.log("[DEBUG] PODAlerts: Number of events:", Object.keys(data).length);
        
        // Log each event structure
        Object.entries(data).forEach(([eventId, eventData]) => {
          console.log(`[DEBUG] Event ${eventId}:`, eventData);
          console.log(`[DEBUG] Event ${eventId} keys:`, Object.keys(eventData));
          if (eventData.markets) {
            console.log(`[DEBUG] Event ${eventId} markets count:`, eventData.markets.length);
            console.log(`[DEBUG] Event ${eventId} markets:`, eventData.markets);
          }
        });
        
        setEvents(data);
        setLastUpdate(new Date());
        setRetryCount(0); // Reset retry count on success
        setLoading(false); // FIXED: Set loading to false on successful data fetch
        console.log("[DEBUG] PODAlerts: Successfully updated events state");
      } else {
        const errorText = await res.text();
        console.error("[DEBUG] PODAlerts: Response not ok, error text:", errorText);
        throw new Error(`Failed to fetch events data: ${errorText}`);
      }
    } catch (e) {
      console.error("[DEBUG] PODAlerts: Error in fetchEvents:", e);
      const newRetryCount = retryCount + 1;
      setRetryCount(newRetryCount);
      if (newRetryCount >= MAX_RETRIES) {
        setError(`Error fetching events data: ${e instanceof Error ? e.message : 'Unknown error'}`);
        setLoading(false);
      }
    }
  }, [retryCount]);

  // Polling logic
  useEffect(() => {
    fetchEvents();
    const poller = setInterval(fetchEvents, POLL_INTERVAL);
    return () => clearInterval(poller);
  }, [fetchEvents]);

  // Reset retry count when user manually refreshes
  const handleManualRefresh = useCallback(() => {
    setRetryCount(0);
    setLoading(true);
    fetchEvents();
  }, [fetchEvents]);

  // Test connection function
  const testConnection = useCallback(async () => {
    try {
      console.log("[DEBUG] Testing backend connection...");
      const res = await fetch('http://localhost:5001/test');
      const data = await res.json();
      console.log("[DEBUG] Test response:", data);
      alert(`Backend connection test: ${data.message}`);
    } catch (e) {
      console.error("[DEBUG] Test connection failed:", e);
      alert(`Backend connection failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  }, []);

  // Auto-dismiss logic
  useEffect(() => {
    const now = Date.now();
    Object.entries(events).forEach(([eventId, event]) => {
      if (dismissed.has(eventId)) return;
      const msSinceAlert = now - (event.alert_arrival_timestamp * 1000);
      if (msSinceAlert > AUTO_DISMISS_MS) {
        setDismissed(prev => new Set(prev).add(eventId));
      }
    });
  }, [events, dismissed]);

  const handleDismiss = useCallback((eventId: string) => {
    setDismissed(prev => new Set(prev).add(eventId));
  }, []);

  const handleEVClick = (event: EventData, market: Market) => {
    setModalMarket({ event, market });
  };

  const closeModal = () => setModalMarket(null);

  // Helper to sort markets by EV descending
  const sortMarkets = (markets: Market[]) => {
    return [...markets].sort((a, b) => {
      const evA = parseFloat(a.ev);
      const evB = parseFloat(b.ev);
      return evB - evA;
    });
  };

  // Helper to get the best EV for an event
  const getBestEV = (markets: Market[]) => {
    if (!markets || markets.length === 0) return -Infinity;
    return Math.max(...markets.map(m => parseFloat(m.ev)));
  };

  // Sort events by best EV
  const activeEvents = Object.entries(events)
    .filter(([eventId]) => !dismissed.has(eventId))
    .sort(([, a], [, b]) => getBestEV(b.markets) - getBestEV(a.markets));

  // Helper to format start time in Central Time, 12-hour format
  const formatStartTime = (isoString: string) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    // Format: M/D/YY h:mm AM/PM in Central Time
    return date.toLocaleString('en-US', {
      timeZone: 'America/Chicago',
      year: '2-digit',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  console.log("[DEBUG] PODAlerts: Rendering - total events:", Object.keys(events).length);
  console.log("[DEBUG] PODAlerts: Rendering - dismissed events:", Array.from(dismissed));
  console.log("[DEBUG] PODAlerts: Rendering - active events:", activeEvents.length);
  console.log("[DEBUG] PODAlerts: Rendering - active event IDs:", activeEvents.map(([id]) => id));

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle1">
            POD Alerts
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Last update: {lastUpdate.toLocaleTimeString()}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            startIcon={<RefreshIcon />}
            onClick={handleManualRefresh}
            disabled={loading}
            variant="outlined"
            size="small"
          >
            Refresh
          </Button>
          <Button
            onClick={testConnection}
            variant="outlined"
            size="small"
            color="secondary"
          >
            Test Connection
          </Button>
          <Button
            onClick={() => setShowOnlyEV(ev => !ev)}
            variant={showOnlyEV ? "contained" : "outlined"}
            size="small"
            color="success"
          >
            {showOnlyEV ? "Show All" : "Show +EV Only"}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
          <CircularProgress />
        </Box>
      ) : activeEvents.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center', background: '#232b3b' }}>
          <Typography variant="body1" color="text.secondary">
            No active alerts at the moment
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={2} wrap="wrap">
          {activeEvents
            .filter(([, event]) => !showOnlyEV || getBestEV(event.markets) > 0)
            .map(([eventId, event]) => {
              const bestEV = getBestEV(event.markets);
              return (
                <Grid item xs={12} sm={12} md={6} key={eventId} sx={{ maxWidth: 900, width: '100%' }}>
                  <Paper sx={{ mb: 2, p: 2, background: '#232b3b', borderRadius: 3, boxShadow: 3, maxWidth: 900, width: '100%' }} className="event-container">
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Box>
                        <Typography variant="subtitle1" className="event-title">{event.title}</Typography>
                        <Typography variant="body2" className="event-meta-info">
                          {event.meta_info}
                          {event.start_time && (
                            <span> | {formatStartTime(event.start_time)}</span>
                          )}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Alert: {event.alert_description} {event.alert_meta}
                          {event.old_odds && event.new_odds && (
                            (() => {
                              const oldOdds = parseFloat(event.old_odds);
                              const newOdds = parseFloat(event.new_odds);
                              if (!isNaN(oldOdds) && !isNaN(newOdds)) {
                                const drop = oldOdds - newOdds;
                                const dropPct = (drop / Math.abs(oldOdds)) * 100;
                                return <span> | Drop: {drop > 0 ? '-' : ''}{Math.abs(drop).toFixed(2)} ({dropPct.toFixed(1)}%)</span>;
                              }
                              return null;
                            })()
                          )}
                        </Typography>
                      </Box>
                      <Button onClick={() => handleDismiss(eventId)} variant="outlined" color="secondary" size="small">
                        Dismiss
                      </Button>
                    </Box>
                    
                    <TableContainer component={Paper} sx={{ background: 'transparent', boxShadow: 'none', width: '100%', maxWidth: 900, overflowX: 'hidden' }}>
                      <Table size="small" aria-label="Odds Table" sx={{ width: '100%', tableLayout: 'auto' }}>
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', textAlign: 'left', pl: 0, whiteSpace: 'normal' }}>Selection</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 'bold' }}>Line</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 'bold' }}>Pinnacle NVP</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 'bold' }}>BetBCK Odds</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 'bold' }}>EV %</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {sortMarkets(event.markets).map((market, idx) => {
                            const ev = parseFloat(market.ev);
                            const isPositiveEV = ev > 0;
                            const isBestEV = ev === bestEV && isPositiveEV;
                            let homeTeam = '', awayTeam = '';
                            if (event.title && event.title.includes(' vs ')) {
                              [homeTeam, awayTeam] = event.title.split(' vs ');
                            }
                            let selectionDisplay = market.selection;
                            if (market.market.toLowerCase().includes('moneyline') || market.market.toLowerCase().includes('spread')) {
                              if (market.selection === 'Home') selectionDisplay = homeTeam;
                              else if (market.selection === 'Away') selectionDisplay = awayTeam;
                            }
                            let evDisplay = market.ev;
                            if (!evDisplay.startsWith('-') && !evDisplay.startsWith('0') && !evDisplay.startsWith('+')) {
                              evDisplay = '+' + evDisplay;
                            }
                            let lineDisplay = market.market.toLowerCase() === 'moneyline' ? 'ML' : (market.market.toLowerCase().includes('moneyline') ? 'ML' : (market.market.toLowerCase().includes('spread') && market.line && !market.line.startsWith('-') && !market.line.startsWith('+') ? `+${market.line}` : market.line));
                            return (
                              <TableRow
                                key={idx}
                                sx={{
                                  background: isBestEV ? 'rgba(0, 255, 0, 0.12)' : isPositiveEV ? 'rgba(25, 60, 26, 0.18)' : undefined,
                                  '&:hover': {
                                    background: isBestEV ? 'rgba(0, 255, 0, 0.18)' : isPositiveEV ? 'rgba(25, 60, 26, 0.28)' : 'rgba(255, 255, 255, 0.05)'
                                  },
                                  height: 30,
                                  '.MuiTableCell-root': { padding: '2px 6px', fontSize: '0.93rem' }
                                }}
                              >
                                <TableCell sx={{ textAlign: 'left', pl: 0, whiteSpace: 'normal' }}>{selectionDisplay}</TableCell>
                                <TableCell align="center">{lineDisplay}</TableCell>
                                <TableCell align="center">{market.pinnacle_nvp && !market.pinnacle_nvp.startsWith('-') && !market.pinnacle_nvp.startsWith('+') ? `+${market.pinnacle_nvp}` : market.pinnacle_nvp}</TableCell>
                                <TableCell align="center">{market.betbck_odds}</TableCell>
                                <TableCell align="center">
                                  <Button
                                    variant="text"
                                    color={isPositiveEV ? 'success' : 'inherit'}
                                    onClick={() => handleEVClick(event, market)}
                                    sx={{
                                      fontWeight: isBestEV ? 'bold' : isPositiveEV ? 'bold' : 'normal',
                                      '&:hover': {
                                        background: isBestEV ? 'rgba(0, 255, 0, 0.12)' : isPositiveEV ? 'rgba(25, 60, 26, 0.12)' : undefined
                                      },
                                      minWidth: 0,
                                      padding: '2px 6px',
                                      fontSize: '0.93rem',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 0.5
                                    }}
                                  >
                                    {isBestEV && <StarIcon fontSize="small" sx={{ color: 'gold', mr: 0.5 }} />}
                                    {evDisplay}
                                  </Button>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Paper>
                </Grid>
              );
            })}
        </Grid>
      )}

      <Dialog open={!!modalMarket} onClose={closeModal} maxWidth="sm" fullWidth>
        <DialogTitle>Bet Details</DialogTitle>
        <DialogContent>
          {modalMarket && (
            <LiveEVModal event={modalMarket.event} market={modalMarket.market} />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeModal}>Close</Button>
          <Button variant="contained" color="success" disabled>Place Bet (Coming Soon)</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// Live-updating modal for EV and Pinnacle NVP
const LiveEVModal: React.FC<{ event: EventData; market: Market }> = ({ event, market }) => {
  const [liveMarket, setLiveMarket] = useState<Market>(market);
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:5001/get_active_events_data');
        if (res.ok) {
          const data = await res.json();
          const updatedEvent = data[event.title];
          if (updatedEvent) {
            const updatedMarket = updatedEvent.markets.find((m: Market) =>
              m.market === market.market && m.selection === market.selection && m.line === market.line
            );
            if (updatedMarket) setLiveMarket(updatedMarket);
          }
        }
      } catch {}
    }, 3000);
    return () => clearInterval(interval);
  }, [event, market]);
  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle1" gutterBottom>{event.title}</Typography>
      <Typography variant="body2" gutterBottom>Market: {liveMarket.market}</Typography>
      <Typography variant="body2" gutterBottom>Selection: {liveMarket.selection}</Typography>
      <Typography variant="body2" gutterBottom>Line: {liveMarket.line}</Typography>
      <Typography variant="body2" gutterBottom>Pinnacle NVP: {liveMarket.pinnacle_nvp}</Typography>
      <Typography variant="body2" gutterBottom>BetBCK Odds: {liveMarket.betbck_odds}</Typography>
      <Typography
        variant="body2"
        color={parseFloat(liveMarket.ev) > 0 ? 'success.main' : 'text.primary'}
        sx={{ fontWeight: 'bold' }}
      >
        EV: {liveMarket.ev}
      </Typography>
    </Box>
  );
};

export default PODAlerts; 