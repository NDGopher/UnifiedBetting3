# WebSockets Explained

## **What are WebSockets?**

Think of WebSockets like a **phone call** between your frontend and backend, instead of the current **text messaging** (polling).

## **Current System (Polling)**
```
Frontend: "Any new alerts?" 
Backend: "No"
Frontend: "Any new alerts?" 
Backend: "No"
Frontend: "Any new alerts?" 
Backend: "Yes! Here's a new alert"
```

**Problems:**
- Frontend asks every 2 seconds (1800 times per hour!)
- Most responses are "No" (waste of resources)
- Delays up to 2 seconds for new alerts

## **WebSocket System**
```
Frontend: "Call me when you have alerts"
Backend: "Got it, I'll call you"
[Phone call stays open]
Backend: "RING! New alert!"
Frontend: "Got it!"
```

**Benefits:**
- Real-time updates (no delay)
- Much less network traffic
- Better performance
- Lower CPU/memory usage

## **How it Works**

### **1. Connection Setup**
```javascript
// Frontend connects once
const ws = new WebSocket('ws://localhost:5001/ws');
ws.onopen = () => console.log('Connected!');
```

### **2. Real-time Updates**
```javascript
// Backend sends data when available
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'new_alert') {
    setEvents(prev => ({...prev, [data.eventId]: data.event}));
  }
};
```

### **3. Backend Implementation**
```python
# Backend sends updates when alerts arrive
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Send new alerts immediately
        if new_alert_available:
            await websocket.send_text(json.dumps(new_alert))
```

## **Why It's Better**

| Aspect | Polling | WebSocket |
|--------|---------|-----------|
| **Speed** | 2-second delay | Instant |
| **Network** | 1800 requests/hour | 1 connection |
| **CPU** | High (constant requests) | Low |
| **Memory** | High (processing responses) | Low |
| **Reliability** | Good | Better |

## **Migration Strategy**

1. **Phase 1**: Keep polling, add WebSocket as backup
2. **Phase 2**: Use WebSocket for new alerts, polling for status
3. **Phase 3**: Full WebSocket implementation

## **Example Implementation**

### **Frontend (React)**
```typescript
const useWebSocket = () => {
  const [events, setEvents] = useState({});
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:5001/ws');
    
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'pod_alert') {
        setEvents(prev => ({...prev, [data.eventId]: data.event}));
      }
    };
    
    return () => ws.close();
  }, []);
  
  return { events, connected };
};
```

### **Backend (FastAPI)**
```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# When new alert arrives
async def handle_new_alert(event_data):
    await manager.broadcast(json.dumps({
        "type": "pod_alert",
        "eventId": event_data["eventId"],
        "event": event_data
    }))
```

## **Benefits for Your System**

1. **Faster Alerts**: No 2-second delay
2. **Better Performance**: Less CPU/memory usage
3. **More Reliable**: Fewer network issues
4. **Scalable**: Can handle more concurrent users
5. **Real-time**: True live updates

## **When to Implement**

- **Now**: Keep current polling (it works)
- **Later**: Add WebSocket for better performance
- **Future**: Full WebSocket migration

The current polling system works fine, but WebSockets would make it much more efficient and responsive! 