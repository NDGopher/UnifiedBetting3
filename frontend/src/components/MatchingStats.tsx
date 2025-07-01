import React, { useState, useEffect } from 'react';
import { Box, Typography, Tooltip } from '@mui/material';
import { useWebSocket } from '../hooks/useWebSocket';

interface MatchingStats {
  pinnacleEvents: number;
  betbckMatches: number;
  matchRate: number;
}

const MatchingStats: React.FC = () => {
  const [stats, setStats] = useState<MatchingStats>({
    pinnacleEvents: 0,
    betbckMatches: 0,
    matchRate: 0
  });

  const { lastMessage } = useWebSocket('ws://localhost:8000/ws');

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);
        
        // Update stats based on WebSocket messages
        if (data.type === 'buckeye_results') {
          setStats({
            pinnacleEvents: data.total_processed || 0,
            betbckMatches: data.total_matched || 0,
            matchRate: data.match_rate || 0
          });
        }
      } catch (error) {
        // Ignore parsing errors for other message types
      }
    }
  }, [lastMessage]);

  // Don't show if no data
  if (stats.pinnacleEvents === 0) {
    return null;
  }

  return (
    <Tooltip 
      title={`Match Rate: ${stats.matchRate.toFixed(1)}%`}
      placement="bottom"
      arrow
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1.5,
          py: 0.5,
          borderRadius: '12px',
          background: 'rgba(0, 212, 255, 0.05)',
          border: '1px solid rgba(0, 212, 255, 0.1)',
          cursor: 'default',
          transition: 'all 0.2s ease',
          '&:hover': {
            background: 'rgba(0, 212, 255, 0.1)',
            border: '1px solid rgba(0, 212, 255, 0.2)',
          }
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <Typography
            variant="caption"
            sx={{
              color: 'rgba(255, 255, 255, 0.5)',
              fontSize: '0.65rem',
              fontWeight: 500,
              display: 'block',
              lineHeight: 1
            }}
          >
            PINNACLE
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: '#00d4ff',
              fontSize: '0.75rem',
              fontWeight: 700,
              lineHeight: 1
            }}
          >
            {stats.pinnacleEvents}
          </Typography>
        </Box>
        
        <Box
          sx={{
            width: '1px',
            height: '20px',
            background: 'rgba(0, 212, 255, 0.2)'
          }}
        />
        
        <Box sx={{ textAlign: 'center' }}>
          <Typography
            variant="caption"
            sx={{
              color: 'rgba(255, 255, 255, 0.5)',
              fontSize: '0.65rem',
              fontWeight: 500,
              display: 'block',
              lineHeight: 1
            }}
          >
            MATCHED
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: stats.matchRate >= 80 ? '#4caf50' : stats.matchRate >= 60 ? '#ff9800' : '#f44336',
              fontSize: '0.75rem',
              fontWeight: 700,
              lineHeight: 1
            }}
          >
            {stats.betbckMatches}
          </Typography>
        </Box>
      </Box>
    </Tooltip>
  );
};

export default MatchingStats; 