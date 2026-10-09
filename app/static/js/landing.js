function landingPage(event) {
  return {
    event: event || null,
    countdown: {
      days: '00',
      hours: '00',
      minutes: '00',
      seconds: '00',
    },
    _countdownTimer: null,

    init() {
      if (!this.event || !this.event.closes_at) {
        this.countdown = { days: '00', hours: '00', minutes: '00', seconds: '00' };
        return;
      }
      this._startCountdown();
    },

    _startCountdown() {
      if (this._countdownTimer) {
        clearInterval(this._countdownTimer);
      }
      this._updateCountdown();
      this._countdownTimer = setInterval(() => this._updateCountdown(), 1000);
    },

    _updateCountdown() {
      const closesAt = this.event.closes_at ? new Date(this.event.closes_at) : null;
      if (!closesAt || Number.isNaN(closesAt.getTime())) {
        this.countdown = { days: '00', hours: '00', minutes: '00', seconds: '00' };
        return;
      }
      const diff = closesAt.getTime() - Date.now();
      if (diff <= 0) {
        this.countdown = { days: '00', hours: '00', minutes: '00', seconds: '00' };
        clearInterval(this._countdownTimer);
        this._countdownTimer = null;
        return;
      }
      const totalSeconds = Math.floor(diff / 1000);
      const days = Math.floor(totalSeconds / 86400);
      const hours = Math.floor((totalSeconds % 86400) / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      const pad = (value) => String(value).padStart(2, '0');
      this.countdown = {
        days: pad(days),
        hours: pad(hours),
        minutes: pad(minutes),
        seconds: pad(seconds),
      };
    },
  };
}
