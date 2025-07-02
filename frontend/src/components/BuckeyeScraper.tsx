import React, { useState } from 'react';
import { Box, Button, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, CircularProgress, Alert } from '@mui/material';
import MatchingStats from './MatchingStats';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
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
        setTopMarkets(allMarkets.length > 0 ? allMarkets.slice(0, 10) : []);
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

  return (
    <Paper sx={{
      p: 2,
      borderRadius: 3,
      boxShadow: 4,
      background: 'linear-gradient(135deg, rgba(20, 25, 35, 0.95) 0%, rgba(15, 20, 30, 0.98) 100%)',
      border: '1px solid rgba(255,255,255,0.1)',
      position: 'relative',
      overflow: 'hidden',
      minHeight: 350,
      '&::before': {
        content: '""',
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '3px',
        background: 'linear-gradient(90deg, #00d4ff 0%, #ff6b35 100%)',
      },
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.2rem', letterSpacing: '-0.01em', color: '#fff' }}>
          BuckeyeScraper EV
        </Typography>
        <Button variant="contained" color="primary" onClick={handleGetEventIds} disabled={loading} sx={{ ml: 2, fontWeight: 700, fontSize: '0.95rem' }}>
          GET EVENT IDS
        </Button>
        <Button variant="contained" color="secondary" onClick={handleRunCalculations} disabled={loading} sx={{ fontWeight: 700, fontSize: '0.95rem' }}>
          RUN CALCULATIONS
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <MatchingStats pinnacleEvents={stats.pinnacleEvents} betbckMatches={stats.betbckMatches} matchRate={stats.matchRate} />
      </Box>
      {lastUpdate && (
        <Typography variant="body2" sx={{ color: '#aaa', mb: 1, ml: 1 }}>
          Last Updated: {dayjs(lastUpdate).format('YYYY-MM-DD HH:mm:ss')} ({dayjs(lastUpdate).fromNow()})
        </Typography>
      )}
      {loading && <CircularProgress sx={{ mb: 2 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      <TableContainer component={Paper} sx={{ background: 'rgba(34,34,34,0.95)', borderRadius: 2, boxShadow: 0, border: '1px solid rgba(255,255,255,0.07)' }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ background: 'linear-gradient(90deg, #00d4ff 0%, #ff6b35 100%)' }}>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>Matchup</TableCell>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>League</TableCell>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>Bet</TableCell>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>BetBCK Odds</TableCell>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>Pinnacle NVP</TableCell>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>EV</TableCell>
              <TableCell sx={{ color: '#fff', fontWeight: 700, fontSize: '1rem', borderBottom: '2px solid #222' }}>Start Time</TableCell>
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
                  <TableCell sx={{ color: '#fff', fontWeight: 500 }}>{row.betbck_odds}</TableCell>
                  <TableCell sx={{ color: '#fff', fontWeight: 500 }}>{row.pinnacle_nvp}</TableCell>
                  <TableCell sx={{ color: '#fff', fontWeight: 700 }}>{row.ev}</TableCell>
                  <TableCell sx={{ color: '#fff', fontWeight: 500 }}>{row.start_time}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default BuckeyeScraper; 