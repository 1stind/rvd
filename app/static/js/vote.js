function votePage(team, event, createPaymentUrl, paymentStatusUrl) {
  return {
    team: team,
    event: event,
    payment: null,

    voter: {
      name: '',
      email: '',
      phone: '',
    },

    qty: 1,
    step: 1,
    error: '',
    phoneError: '',
    isLoading: false,

    showQrModal: false,
    showSuccessModal: false,
    showMockSimulator: false,

    pollInterval: null,

    createPaymentUrl,
    paymentStatusUrl,

    get isVotingOpen() {
      if (!this.event) return false;
      const now = new Date();
      const opensAt = this.event.opens_at ? new Date(this.event.opens_at) : null;
      const closesAt = this.event.closes_at ? new Date(this.event.closes_at) : null;
      if (opensAt && now < opensAt) return false;
      if (closesAt && now > closesAt) return false;
      return true;
    },

    get votingStatus() {
      if (!this.event) return 'closed';
      if (!this.isVotingOpen) return 'closed';
      return 'open';
    },

    // =========================
    // INIT
    // =========================
    init() {
      console.log('[OK] Alpine votePage init');

      this.$watch('voter.phone', (value) => {
        if (!value) {
          this.phoneError = 'Nomor WhatsApp wajib diisi.';
        } else if (!/^\d{9,13}$/.test(value)) {
          this.phoneError = 'Format nomor tidak valid';
        } else {
          this.phoneError = '';
        }
      });

      this.$watch('qty', (value) => {
        if (!value || value < 1) {
          this.qty = 1;
        }
      });
    },

    // =========================
    // FORMAT
    // =========================
    calculateTotal() {
      return;
    },

    formatCurrency(amount) {
      return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
      }).format(amount || 0);
    },

    get totalPrice() {
      return (this.event?.price_per_vote || 0) * (this.qty || 0);
    },

    // =========================
    // QTY
    // =========================
    incrementQty() {
      this.qty++;
    },

    decrementQty() {
      if (this.qty > 1) this.qty--;
    },

    // =========================
    // STEP
    // =========================
    nextStep() {
      this.error = '';

      if (!this.voter.name) {
        this.error = 'Nama wajib diisi';
        return;
      }

      if (this.phoneError || !this.voter.phone) {
        this.error = this.phoneError || 'Nomor wajib diisi';
        return;
      }

      this.step = 2;
    },

    // =========================
    // CREATE INVOICE
    // =========================
    async createInvoice() {
      this.error = '';

      if (!this.voter.phone) {
        this.error = 'Nomor wajib diisi';
        return;
      }

      this.isLoading = true;

      const payload = {
        event_id: this.event?.id,
        team_id: this.team?.id,
        qty: this.qty,
        supporter_name: this.voter.name,
        supporter_email: this.voter.email,
        supporter_phone: `+62${this.voter.phone}`,
        is_anonymous: false,
      };

      try {
      const res = await fetch(this.createPaymentUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

        const data = await res.json();

        if (!res.ok) throw new Error(data.message || 'Gagal');

        // 🔥 SIMPAN PAYMENT
        this.payment = data.data;

        // 🔥 BUKA QR / MOCK SIMULATOR MODAL
        // Mock mode is signalled by an explicit is_mock flag (qr_string starts
        // with WVC2026 when MIDTRANS_SERVER_KEY is empty). Using the flag avoids
        // sniffing the payment provider from the QR string contents.
        if (this.payment.is_mock) {
          this.showMockSimulator = true;
        } else {
          this.showQrModal = true;
        }

         // polling status
         this.startPolling();
      } catch (e) {
        this.error = e.message;
      } finally {
        this.isLoading = false;
      }
    },

    // =========================
    // POLLING
    // =========================
    startPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval);
      }

      this.pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`${this.paymentStatusUrl}/${this.payment.id}/status`);
          const data = await res.json();

          if (data.data.status === 'SUCCESS') {
            clearInterval(this.pollInterval);

            this.showQrModal = false;
            this.showMockSimulator = false;
            this.showSuccessModal = true;

            this.payment = data.data;
          } else if (data.data.status === 'FAILED') {
            clearInterval(this.pollInterval);

            this.showQrModal = false;
            this.showMockSimulator = false;
            this.showSuccessModal = false;
            this.error = 'Pembayaran gagal. Silakan kembali dan coba lagi.';
          } else if (data.data.status === 'EXPIRED' || data.data.status === 'CANCELED') {
            clearInterval(this.pollInterval);

            this.showQrModal = false;
            this.showMockSimulator = false;
            this.showSuccessModal = false;
            this.error = 'Invoice telah kedaluwarsa. Silakan kembali dan coba lagi.';
          }
        } catch (e) {
          console.log('Polling error');
        }
      }, 5000);
    },

    // =========================
    // MOCK SIMULATOR
    // =========================
    async simulate(action) {
      this.error = '';
      try {
        const res = await fetch(`${this.paymentStatusUrl}/mock/${this.payment.id}/simulate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.message || 'Gagal');

        this.payment = data.data;

        // Tutup simulator untuk status terminal; biarkan polling mendeteksi
        // SUCCESS/FAILED dan menampilkan modal/error yang sesuai.
        // Untuk PENDING, pertahankan simulator agar bisa disimulasikan lagi.
        if (this.payment.status !== 'PENDING') {
          this.showMockSimulator = false;
        }
      } catch (e) {
        this.error = e.message;
      }
    },

    // =========================
    // CLOSE MODAL
    // =========================
    closeModal() {
      this.showQrModal = false;
    },
  };
}