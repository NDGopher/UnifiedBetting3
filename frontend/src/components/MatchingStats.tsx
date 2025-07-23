import React from 'react';
import { Box, Typography, Tooltip } from '@mui/material';

interface MatchingStatsProps {
  pinnacleEvents: number;
  betbckMatches: number;
  matchRate: number;
}

const MatchingStats: React.FC<MatchingStatsProps> = ({ pinnacleEvents, betbckMatches, matchRate }) => {
  if (pinnacleEvents === 0) {
    return null;
  }

  return (
    <Tooltip 
      title={`Match Rate: ${matchRate.toFixed(1)}%`}
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
            {pinnacleEvents}
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
              color: matchRate >= 80 ? '#4caf50' : matchRate >= 60 ? '#ff9800' : '#f44336',
              fontSize: '0.75rem',
              fontWeight: 700,
              lineHeight: 1
            }}
          >
            {betbckMatches}
          </Typography>
        </Box>
      </Box>
    </Tooltip>
  );
};

export default MatchingStats; 