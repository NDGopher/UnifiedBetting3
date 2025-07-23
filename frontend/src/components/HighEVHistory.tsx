import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Box,
  Chip,
  IconButton,
  Collapse
} from '@mui/material';
import { History, ExpandMore, ExpandLess } from '@mui/icons-material';

interface HighEVAlert {
  id: number;
  event_id: string;
  sport: string;
  away_team: string;
  home_team: string;
  ev_percentage: number;
  bet_type: string;
  odds: string;
  nvp: string;
  created_at: string;
  processed: string;
}

const HighEVHistory: React.FC = () => {
  const [showHistory, setShowHistory] = useState(false);
  const [alerts, setAlerts] = useState<HighEVAlert[]>([]);
  const [loading, setLoading] = useState(false);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch('/high-ev-alerts');
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      } else {
        console.error('Failed to load high EV alerts');
      }
    } catch (error) {
      console.error('Error loading high EV alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEVColor = (ev: number) => {
    if (ev > 10) return '#e53935'; // Red for high EV
    if (ev > 5) return '#ffb300'; // Orange for medium EV
    return '#43a047'; // Green for low EV
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Alerts with EV &gt; 3% are automatically saved to the database
        </Typography>
        <Button
          variant="outlined"
          onClick={() => {
            setShowHistory(!showHistory);
            if (!showHistory) loadHistory();
          }}
          startIcon={showHistory ? <ExpandLess /> : <ExpandMore />}
        >
          {showHistory ? 'Hide' : 'Show'} History
        </Button>
      </Box>

      <Collapse in={showHistory}>
        {loading ? (
          <Typography>Loading...</Typography>
        ) : alerts.length > 0 ? (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Sport</TableCell>
                  <TableCell>Teams</TableCell>
                  <TableCell>EV %</TableCell>
                  <TableCell>Bet</TableCell>
                  <TableCell>Odds</TableCell>
                  <TableCell>NVP</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id} hover>
                    <TableCell>{formatDateTime(alert.created_at)}</TableCell>
                    <TableCell>
                      <Chip 
                        label={alert.sport} 
                        size="small" 
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {alert.away_team} vs {alert.home_team}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${alert.ev_percentage}%`}
                        size="small"
                        sx={{
                          backgroundColor: getEVColor(alert.ev_percentage),
                          color: 'white',
                          fontWeight: 'bold'
                        }}
                      />
                    </TableCell>
                    <TableCell>{alert.bet_type}</TableCell>
                    <TableCell>{alert.odds}</TableCell>
                    <TableCell>{alert.nvp}</TableCell>
                    <TableCell>
                      <Chip
                        label={alert.processed}
                        size="small"
                        color={alert.processed === 'processed' ? 'success' : 'warning'}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No high EV alerts found. Alerts with EV &gt; 3% will appear here.
          </Typography>
        )}
      </Collapse>
    </Box>
  );
};

export default HighEVHistory; 