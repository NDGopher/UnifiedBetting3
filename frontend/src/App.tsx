import React, { createContext, useRef, useContext } from "react";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { AppBar, Toolbar, IconButton } from "@mui/material";
import { TrendingUp, Analytics, Calculate } from "@mui/icons-material";
import PODAlerts from "./components/PODAlerts";
import EVCalculator from "./components/EVCalculator";
import PropBuilder from "./components/PropBuilder";

// Modern dark theme inspired by Onlook
const modernTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00d4ff",
      light: "#4de6ff",
      dark: "#0099cc",
    },
    secondary: {
      main: "#ff6b35",
      light: "#ff9568",
      dark: "#cc4a1a",
    },
    background: {
      default: "#0a0a0a",
      paper: "rgba(20, 25, 35, 0.95)",
    },
    text: {
      primary: "#ffffff",
      secondary: "rgba(255, 255, 255, 0.7)",
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h6: {
      fontWeight: 600,
      letterSpacing: "-0.01em",
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage:
            "linear-gradient(135deg, rgba(20, 25, 35, 0.95) 0%, rgba(15, 20, 30, 0.98) 100%)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "12px",
          backdropFilter: "blur(10px)",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background:
            "linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
        },
      },
    },
  },
});

// Context for BetBCK tab reference
export const BetbckTabContext = createContext<{ betbckTabRef: React.MutableRefObject<Window | null> }>({ betbckTabRef: { current: null } });

function openBetbckTabOnLoad(betbckTabRef: React.MutableRefObject<Window | null>) {
  if (!betbckTabRef.current || betbckTabRef.current.closed) {
    betbckTabRef.current = window.open('https://betbck.com', 'betbck_tab');
  }
}

function App() {
  const betbckTabRef = useRef<Window | null>(null);

  React.useEffect(() => {
    openBetbckTabOnLoad(betbckTabRef);
  }, []);

  return (
    <BetbckTabContext.Provider value={{ betbckTabRef }}>
      <ThemeProvider theme={modernTheme}>
        <CssBaseline />
        <Box
          sx={{
            minHeight: "100vh",
            background:
              "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%)",
          }}
        >
          {/* Modern Header */}
          <AppBar position="static" elevation={0}>
            <Toolbar sx={{ py: 1 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    p: 1,
                    borderRadius: "8px",
                    background: "rgba(0, 212, 255, 0.1)",
                    border: "1px solid rgba(0, 212, 255, 0.2)",
                  }}
                >
                  <TrendingUp sx={{ color: "#00d4ff" }} />
                  <Typography
                    variant="h6"
                    component="div"
                    sx={{
                      fontWeight: 700,
                      background:
                        "linear-gradient(135deg, #00d4ff 0%, #ffffff 100%)",
                      backgroundClip: "text",
                      WebkitBackgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                    }}
                  >
                    Unified Betting
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ flexGrow: 1 }} />
              <Box sx={{ display: "flex", gap: 1 }}>
                <IconButton sx={{ color: "rgba(255, 255, 255, 0.7)" }}>
                  <Analytics />
                </IconButton>
                <IconButton sx={{ color: "rgba(255, 255, 255, 0.7)" }}>
                  <Calculate />
                </IconButton>
              </Box>
            </Toolbar>
          </AppBar>
          <Container maxWidth="xl" sx={{ py: 4 }}>
            <Grid container spacing={3}>
              {/* POD Alerts Section */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    "&::before": {
                      content: '""',
                      position: "absolute",
                      top: 0,
                      left: 0,
                      right: 0,
                      height: "3px",
                      background:
                        "linear-gradient(90deg, #00d4ff 0%, #ff6b35 100%)",
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <TrendingUp sx={{ color: "#00d4ff" }} />
                    <Typography
                      component="h2"
                      variant="h6"
                      sx={{ color: "#ffffff", fontWeight: 700 }}
                    >
                      POD Alerts
                    </Typography>
                    <Box
                      sx={{
                        px: 2,
                        py: 0.5,
                        borderRadius: "20px",
                        background: "rgba(0, 212, 255, 0.1)",
                        border: "1px solid rgba(0, 212, 255, 0.3)",
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "#00d4ff", fontWeight: 600 }}
                      >
                        LIVE
                      </Typography>
                    </Box>
                  </Box>
                  <PODAlerts />
                </Paper>
              </Grid>
              {/* PropBuilder Section */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    "&::before": {
                      content: '""',
                      position: "absolute",
                      top: 0,
                      left: 0,
                      right: 0,
                      height: "3px",
                      background:
                        "linear-gradient(90deg, #ff6b35 0%, #00d4ff 100%)",
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <Analytics sx={{ color: "#ff6b35" }} />
                    <Typography
                      component="h2"
                      variant="h6"
                      sx={{ color: "#ffffff", fontWeight: 700 }}
                    >
                      PropBuilder EV
                    </Typography>
                    <Box
                      sx={{
                        px: 2,
                        py: 0.5,
                        borderRadius: "20px",
                        background: "rgba(255, 107, 53, 0.1)",
                        border: "1px solid rgba(255, 107, 53, 0.3)",
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "#ff6b35", fontWeight: 600 }}
                      >
                        ACTIVE
                      </Typography>
                    </Box>
                  </Box>
                  <PropBuilder />
                </Paper>
              </Grid>
              {/* EV Calculator Section */}
              <Grid item xs={12} md={4} lg={3}>
                <Paper
                  sx={{
                    p: 2,
                    display: "flex",
                    flexDirection: "column",
                    maxHeight: "400px",
                    position: "relative",
                    overflow: "hidden",
                    "&::before": {
                      content: '""',
                      position: "absolute",
                      top: 0,
                      left: 0,
                      right: 0,
                      height: "3px",
                      background:
                        "linear-gradient(90deg, #00d4ff 0%, #ffffff 100%)",
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      mb: 2,
                    }}
                  >
                    <Calculate sx={{ color: "#00d4ff", fontSize: "1.2rem" }} />
                    <Typography
                      component="h3"
                      variant="subtitle1"
                      sx={{ color: "#ffffff", fontWeight: 600 }}
                    >
                      EV Calculator
                    </Typography>
                  </Box>
                  <EVCalculator />
                </Paper>
              </Grid>
            </Grid>
          </Container>
        </Box>
      </ThemeProvider>
    </BetbckTabContext.Provider>
  );
}

export default App;