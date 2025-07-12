import React, { useEffect, useState, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  AlertTitle,
  Typography,
  Box,
  Chip,
  CircularProgress,
} from '@mui/material';
import { Warning as WarningIcon, Error as ErrorIcon } from '@mui/icons-material';

interface BetBCKAlert {
  message: string;
  type: 'success' | 'warning' | 'error' | 'critical';
  timestamp: number;
}

interface BetBCKStatus {
  queue_size: number;
  rate_limited: boolean;
  consecutive_failures: number;
  session_age_minutes: number;
  worker_running: boolean;
  session_valid: boolean;
  frontend_alert?: BetBCKAlert;
}

const BetBCKStatusPopup: React.FC = () => {
  const [betbckStatus, setBetbckStatus] = useState<BetBCKStatus | null>(null);
  const [showPopup, setShowPopup] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Fetch BetBCK status
  const fetchBetbckStatus = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:5001/api/betbck/status');
      if (res.ok) {
        const statusData = await res.json();
        if (statusData.status === 'success') {
          setBetbckStatus(statusData.data);
        }
      }
    } catch (e) {
      console.warn('Failed to fetch BetBCK status:', e);
    }
  }, []);

  // Poll BetBCK status every 5 seconds
  useEffect(() => {
    fetchBetbckStatus();
    const statusPoller = setInterval(fetchBetbckStatus, 5000);
    return () => clearInterval(statusPoller);
  }, [fetchBetbckStatus]);

  // Determine if popup should be shown
  useEffect(() => {
    if (!betbckStatus || dismissed) {
      setShowPopup(false);
      return;
    }

    // Show popup for critical issues
    const shouldShow = 
      betbckStatus.rate_limited || 
      !betbckStatus.worker_running ||
      (betbckStatus.frontend_alert !== undefined && ['critical', 'error'].includes(betbckStatus.frontend_alert.type));

    setShowPopup(shouldShow);

    // Auto-dismiss after issues are resolved
    if (!shouldShow && dismissed) {
      setDismissed(false);
    }
  }, [betbckStatus, dismissed]);

  const handleDismiss = () => {
    setDismissed(true);
    setShowPopup(false);
  };

  if (!showPopup || !betbckStatus) {
    return null;
  }

  const getAlertSeverity = (type: string) => {
    switch (type) {
      case 'critical': return 'error';
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'success': return 'success';
      default: return 'info';
    }
  };

  const getIcon = () => {
    if (betbckStatus.rate_limited || betbckStatus.frontend_alert?.type === 'critical') {
      return <ErrorIcon color="error" />;
    }
    return <WarningIcon color="warning" />;
  };

  const getTitle = () => {
    if (betbckStatus.rate_limited) {
      return 'BetBCK Rate Limited';
    }
    if (!betbckStatus.worker_running) {
      return 'BetBCK Worker Offline';
    }
    if (betbckStatus.frontend_alert) {
      return 'BetBCK System Alert';
    }
    return 'BetBCK Status';
  };

  return (
    <Dialog
      open={showPopup}
      onClose={handleDismiss}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          position: 'fixed',
          top: '20px',
          right: '20px',
          m: 0,
          maxWidth: '400px',
          width: '400px',
        }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pb: 1 }}>
        {getIcon()}
        {getTitle()}
      </DialogTitle>
      
      <DialogContent sx={{ pb: 2 }}>
        {betbckStatus.rate_limited && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>Rate Limited!</AlertTitle>
            BetBCK has rate limited our requests. All scraping has been stopped to prevent further issues.
          </Alert>
        )}

        {!betbckStatus.worker_running && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>Worker Offline</AlertTitle>
            The BetBCK request worker is not running. No new alerts will be processed.
          </Alert>
        )}

        {betbckStatus.frontend_alert && (
          <Alert 
            severity={getAlertSeverity(betbckStatus.frontend_alert.type)} 
            sx={{ mb: 2 }}
          >
            <AlertTitle>System Alert</AlertTitle>
            {betbckStatus.frontend_alert.message}
            <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
              {new Date(betbckStatus.frontend_alert.timestamp * 1000).toLocaleTimeString()}
            </Typography>
          </Alert>
        )}

        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Current Status:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
            <Chip 
              label={`Queue: ${betbckStatus.queue_size}`} 
              size="small" 
              color={betbckStatus.queue_size > 10 ? 'warning' : 'default'} 
            />
            <Chip 
              label={`Session: ${betbckStatus.session_age_minutes.toFixed(1)}m`} 
              size="small" 
              color={betbckStatus.session_age_minutes > 25 ? 'warning' : 'default'} 
            />
            <Chip 
              label={betbckStatus.worker_running ? 'Worker: Running' : 'Worker: Offline'} 
              size="small" 
              color={betbckStatus.worker_running ? 'success' : 'error'} 
            />
          </Box>
          
          {betbckStatus.consecutive_failures > 0 && (
            <Typography variant="body2" color="warning.main">
              Consecutive failures: {betbckStatus.consecutive_failures}
            </Typography>
          )}
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleDismiss} color="primary">
          Dismiss
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BetBCKStatusPopup; 