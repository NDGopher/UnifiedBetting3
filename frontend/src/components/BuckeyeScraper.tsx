import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, CircularProgress, Alert } from '@mui/material';
import MatchingStats from './MatchingStats';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { Analytics } from '@mui/icons-material';
dayjs.extend(relativeTime);

interface Market {
  market: string;
  selection: string;
  line: string;
  pinnacle_nvp: string;
  betbck_odds: string;
  ev: string;
}

interface BuckeyeEvent {
  event_id: string;
  home_team: string;
  away_team: string;
  league: string;
  start_time: string;
  markets: Market[];
  total_ev: number;
  best_ev: number;
  last_updated: string;
}

const API_BASE = 'http://localhost:5001';

const BuckeyeScraper: React.FC = () => {
  const [events, setEvents] = useState<BuckeyeEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [topMarkets, setTopMarkets] = useState<any[]>([]);
  const [stats, setStats] = useState({ pinnacleEvents: 0, betbckMatches: 0, matchRate: 0 });
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const isPolling = useRef(false);

  const startPolling = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(() => {
      if (!isPolling.current && !loading) {
        isPolling.current = true;
        fetchAceEvents().finally(() => { isPolling.current = false; });
      }
    }, 3000);
  };

  const stopPolling = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = null;
  };

  const fetchEvents = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      console.log('[BuckeyeScraper] Fetching results...');
      const res = await fetch(`${API_BASE}/buckeye/results`);
      const data = await res.json();
      console.log('[BuckeyeScraper] Results response:', data);
      if (data.status === 'success') {
        setLastUpdate(data.data.last_update || null);
        const allMarkets = data.data.markets || [];
        allMarkets.sort((a: any, b: any) => parseFloat(b.ev) - parseFloat(a.ev));
        // Count positive EV markets
        const positiveEVMarkets = allMarkets.filter((market: any) => parseFloat(market.ev) > 0);
        const displayLimit = positiveEVMarkets.length > 10 ? 25 : 10;
        setTopMarkets(allMarkets.length > 0 ? allMarkets.slice(0, displayLimit) : []);
      } else {
        setError(data.message || 'Failed to fetch results');
        setTopMarkets([]);
      }
    } catch (err) {
      console.error('[BuckeyeScraper] Error fetching results:', err);
      setError('Failed to fetch results');
      setTopMarkets([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGetEventIds = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      console.log('[BuckeyeScraper] Getting event IDs...');
      const res = await fetch(`${API_BASE}/buckeye/get-event-ids`, { method: 'POST' });
      const data = await res.json();
      console.log('[BuckeyeScraper] Get Event IDs response:', data);
      if (data.status === 'success') {
        setMessage(data.message || 'Event IDs retrieved successfully');
        if (data.data && typeof data.data.event_count === 'number') {
          setStats(s => ({ ...s, pinnacleEvents: data.data.event_count }));
        }
      } else {
        setError(data.message || 'Failed to get event IDs');
      }
    } catch (err) {
      console.error('[BuckeyeScraper] Error getting event IDs:', err);
      setError('Failed to get event IDs');
    } finally {
      setLoading(false);
    }
  };

  const handleRunCalculations = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      console.log('[BuckeyeScraper] Running calculations (via pipeline)...');
      const res = await fetch(`${API_BASE}/api/run-pipeline`, { method: 'POST' });
      const data = await res.json();
      console.log('[BuckeyeScraper] Run Calculations (pipeline) response:', data);
      if (data.status === 'success' && data.data && data.data.final_result) {
        setMessage(data.data.final_result.message || 'Calculations completed');
        // Update stats if available
        if (data.data.final_result.data) {
          setStats(s => ({
            ...s,
            pinnacleEvents: data.data.final_result.data.total_events || 0,
            betbckMatches: data.data.final_result.data.total_matches || 0,
            matchRate: data.data.final_result.data.match_rate || 0
          }));
        }
        fetchEvents(); // Only fetch events after calculations
      } else {
        setError(data.message || 'Failed to run calculations');
        setTopMarkets([]);
      }
    } catch (err) {
      console.error('[BuckeyeScraper] Error running calculations:', err);
      setError('Failed to run calculations');
      setTopMarkets([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAceCalculations = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    startPolling(); // Start polling when calculation starts
    try {
      console.log('[BuckeyeScraper] Running Ace calculations...');
      const res = await fetch(`${API_BASE}/ace/run-calculations`, { method: 'POST' });
      const data = await res.json();
      console.log('[BuckeyeScraper] Ace calculations response:', data);
      
      // Handle the new response format with status field
      if (data.status === 'success') {
        setMessage(data.message || 'Ace calculations completed successfully');
        // Fetch Ace results after calculations
        fetchAceEvents();
      } else if (data.status === 'partial_success') {
        setMessage(data.message || 'Ace calculations partially completed');
        // Still fetch results even if partial success
        fetchAceEvents();
      } else if (data.status === 'error') {
        setError(data.message || data.error || 'Failed to run Ace calculations');
        setTopMarkets([]);
        stopPolling(); // Stop polling on error
      } else {
        // Handle old format for backward compatibility
        if (data.message) {
          setMessage(data.message);
          fetchAceEvents();
        } else {
          setError('Failed to run Ace calculations - unexpected response format');
          setTopMarkets([]);
          stopPolling();
        }
      }
    } catch (err) {
      console.error('[BuckeyeScraper] Error running Ace calculations:', err);
      setError('Failed to run Ace calculations - network error');
      setTopMarkets([]);
      stopPolling(); // Stop polling on error
    } finally {
      setLoading(false);
    }
  };

  const fetchAceEvents = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      console.log('[BuckeyeScraper] Fetching Ace results...');
      const res = await fetch(`${API_BASE}/ace/results`);
      const data = await res.json();
      console.log('[BuckeyeScraper] Ace results response:', data);
      
      // Handle the new response format with status field
      if (data.status === 'success') {
        setLastUpdate(data.last_update || null);
        const allMarkets = data.markets || [];
        allMarkets.sort((a: any, b: any) => parseFloat(b.ev) - parseFloat(a.ev));
        // Count positive EV markets
        const positiveEVMarkets = allMarkets.filter((market: any) => parseFloat(market.ev) > 0);
        const displayLimit = positiveEVMarkets.length > 10 ? 25 : 10;
        setTopMarkets(allMarkets.length > 0 ? allMarkets.slice(0, displayLimit) : []);
        stopPolling(); // Stop polling when results are loaded
      } else if (data.status === 'partial_success') {
        setLastUpdate(data.last_update || null);
        const allMarkets = data.markets || [];
        allMarkets.sort((a: any, b: any) => parseFloat(b.ev) - parseFloat(a.ev));
        // Count positive EV markets
        const positiveEVMarkets = allMarkets.filter((market: any) => parseFloat(market.ev) > 0);
        const displayLimit = positiveEVMarkets.length > 10 ? 25 : 10;
        setTopMarkets(allMarkets.length > 0 ? allMarkets.slice(0, displayLimit) : []);
        setMessage(data.message || 'Partial results loaded');
        stopPolling(); // Stop polling when results are loaded
      } else if (data.status === 'error') {
        setError(data.message || data.error || 'Failed to fetch Ace results');
        setTopMarkets([]);
        stopPolling(); // Stop polling on error
      } else {
        // Handle old format for backward compatibility
        if (data.data && data.data.markets) {
          setLastUpdate(data.data.last_update || null);
          const allMarkets = data.data.markets || [];
          allMarkets.sort((a: any, b: any) => parseFloat(b.ev) - parseFloat(a.ev));
          // Count positive EV markets
          const positiveEVMarkets = allMarkets.filter((market: any) => parseFloat(market.ev) > 0);
          const displayLimit = positiveEVMarkets.length > 10 ? 25 : 10;
          setTopMarkets(allMarkets.length > 0 ? allMarkets.slice(0, displayLimit) : []);
          stopPolling(); // Stop polling when results are loaded
        } else {
          setError('Failed to fetch Ace results - unexpected response format');
          setTopMarkets([]);
          stopPolling(); // Stop polling on error
        }
      }
    } catch (err) {
      console.error('[BuckeyeScraper] Error fetching Ace results:', err);
      setError('Failed to fetch Ace results - network error');
      setTopMarkets([]);
      stopPolling(); // Stop polling on error
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', gap: 2, mb: 2, justifyContent: 'flex-start' }}>
        <Button
          variant="outlined"
          size="small"
          sx={{
            color: '#43a047',
            borderColor: '#43a047',
            borderRadius: 2,
            fontWeight: 600,
            px: 1,
            py: 0.25,
            fontSize: '0.92rem',
            minWidth: 0,
            height: 32,
            textTransform: 'none',
            lineHeight: 1.2,
            '&:hover': {
              bgcolor: '#1b2b1b',
              borderColor: '#43a047',
            },
          }}
          onClick={handleGetEventIds}
        >
          Get Event IDs
        </Button>
        <Button
          variant="outlined"
          size="small"
          sx={{
            color: '#b0b3b8',
            borderColor: '#b0b3b8',
            borderRadius: 2,
            fontWeight: 600,
            px: 1,
            py: 0.25,
            fontSize: '0.92rem',
            minWidth: 0,
            height: 32,
            textTransform: 'none',
            lineHeight: 1.2,
            '&:hover': {
              bgcolor: '#23272f',
              borderColor: '#b0b3b8',
            },
          }}
          onClick={handleRunCalculations}
        >
          Buckeye
        </Button>
        <Button
          variant="outlined"
          size="small"
          sx={{
            color: '#b0b3b8',
            borderColor: '#b0b3b8',
            borderRadius: 2,
            fontWeight: 600,
            px: 1,
            py: 0.25,
            fontSize: '0.92rem',
            minWidth: 0,
            height: 32,
            textTransform: 'none',
            lineHeight: 1.2,
            '&:hover': {
              bgcolor: '#23272f',
              borderColor: '#b0b3b8',
            },
          }}
          onClick={handleRunAceCalculations}
        >
          Ace
        </Button>
      </Box>
      {lastUpdate && (
        <Typography variant="body2" sx={{ color: '#aaa', mb: 1, ml: 1 }}>
          Last Updated: {dayjs(lastUpdate).format('YYYY-MM-DD HH:mm:ss')} ({dayjs(lastUpdate).fromNow()})
        </Typography>
      )}
      {loading && <CircularProgress sx={{ mb: 2 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      <TableContainer sx={{ background: 'rgba(34,34,34,0.95)', borderRadius: 2, boxShadow: 0, border: '1px solid rgba(255,255,255,0.07)' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>Matchup</TableCell>
              <TableCell sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>League</TableCell>
              <TableCell sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>Bet</TableCell>
              <TableCell align="center" sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>Book Odds</TableCell>
              <TableCell align="center" sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>Pinnacle NVP</TableCell>
              <TableCell align="center" sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>EV</TableCell>
              <TableCell sx={{ color: '#b0b3b8', fontWeight: 600, fontSize: '1rem' }}>Start Time</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {topMarkets.length === 0 && !loading && !error ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ color: '#888', fontStyle: 'italic' }}>
                  No valid markets found. Click RUN CALCULATIONS to populate or check backend filters.
                </TableCell>
              </TableRow>
            ) : (
              topMarkets.map((row, idx) => (
                <TableRow key={idx}>
                  <TableCell sx={{ color: '#fff', fontWeight: 500 }}>{row.matchup}</TableCell>
                  <TableCell sx={{ color: '#fff', fontWeight: 500 }}>{row.league}</TableCell>
                  <TableCell sx={{ color: '#fff', fontWeight: 500 }}>{row.bet}</TableCell>
                  <TableCell align="center">
                    {row.betbck_odds || row.ace_odds || 'N/A'}
                  </TableCell>
                  <TableCell align="center">
                    {row.pinnacle_nvp}
                  </TableCell>
                  <TableCell align="center">
                    {parseFloat(row.ev) > 0 ? (
                      <Box sx={{
                        display: 'inline-block',
                        px: 1.2,
                        py: 0.2,
                        border: '2px solid #43a047',
                        borderRadius: 1.5,
                        color: '#43a047',
                        fontWeight: 700,
                        fontSize: '1em',
                        bgcolor: '#23272f',
                      }}>
                        {row.ev}
                      </Box>
                    ) : (
                      <span>{row.ev}</span>
                    )}
                  </TableCell>
                  <TableCell align="left">
                    {dayjs(row.start_time).format('M/D/YYYY [at] h:mm A')}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};

export default BuckeyeScraper; 