// Enhanced notification system with different sounds and detailed alerts
class EnhancedNotifier {
  private highSound: HTMLAudioElement;
  private mediumSound: HTMLAudioElement;
  private lowSound: HTMLAudioElement;

  constructor() {
    // Create audio elements for different EV levels
    this.highSound = new Audio('/sounds/high-alert.mp3');
    this.mediumSound = new Audio('/sounds/medium-alert.mp3');
    this.lowSound = new Audio('/sounds/low-alert.mp3');
    
    // Request notification permission on initialization
    this.requestNotificationPermission();
  }

  async requestNotificationPermission() {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      console.log('Notification permission:', permission);
    }
  }

  playSound(ev: number) {
    try {
      if (ev > 10) {
        this.highSound.play();
      } else if (ev > 5) {
        this.mediumSound.play();
      } else if (ev > 2.5) {
        this.lowSound.play();
      }
    } catch (error) {
      console.warn('Could not play sound:', error);
    }
  }

  showNotification(alert: any) {
    if (Notification.permission !== 'granted') {
      return;
    }

    const ev = alert.ev || 0;
    let title = '';
    let icon = '';

    if (ev > 10) {
      title = '🚨 HIGH EV ALERT!';
      icon = '/icons/high-ev.png';
    } else if (ev > 5) {
      title = '⚡ Good EV Alert';
      icon = '/icons/medium-ev.png';
    } else if (ev > 2.5) {
      title = '📊 EV Alert';
      icon = '/icons/low-ev.png';
    } else {
      return; // Don't notify for low EV
    }

    // Play appropriate sound
    this.playSound(ev);

    // Create detailed notification
    const notification = new Notification(title, {
      body: `${alert.sport || 'Unknown Sport'}: ${alert.awayTeam || 'Away'} vs ${alert.homeTeam || 'Home'}\nEV: ${ev}%\nBet: ${alert.bet || 'N/A'}\nOdds: ${alert.odds || 'N/A'}\nNVP: ${alert.nvp || 'N/A'}`,
      icon: icon,
      requireInteraction: true, // Stays until clicked
      tag: alert.eventId, // Groups similar alerts
      badge: '/icons/badge.png'
    });

    // Auto-close after 30 seconds if not clicked
    setTimeout(() => {
      notification.close();
    }, 30000);
  }
}

// Create singleton instance
export const notifier = new EnhancedNotifier();

// Export function for easy use
export const showEnhancedNotification = (alert: any) => {
  notifier.showNotification(alert);
}; 