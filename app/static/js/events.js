function eventsPage(event, allEvents) {
  return {
    event: event || null,
    allEvents: allEvents || [],
    tab: 'peserta',
    eventQuery: '', openOnly: false, participantQuery: '',
    dataPeserta: [],
    dataLeaderboard: [],
    dataDonatur: [],
    participantPage: 1,
    participantsPerPage: 12,
    loadedTabs: {},
    loading: { peserta: false, leaderboard: false, donatur: false },
    error: { peserta: null, leaderboard: null, donatur: null },
    isTransitioning: false,

    init() {
      const params = new URLSearchParams(window.location.search);
      const eventId = params.get('event_id');
      if (eventId) {
        const found = this.allEvents.find(e => e.id == eventId);
        if (found) {
          this.event = found;
        } else {
          this.event = null;
        }
      } else {
        this.event = null;
      }

      window.addEventListener('popstate', () => {
        const params = new URLSearchParams(window.location.search);
        const eventId = params.get('event_id');
        if (eventId) {
          const found = this.allEvents.find(e => e.id == eventId);
          if (found) {
            this.switchEvent(found, false);
          } else {
            this.event = null;
          }
        } else {
          this.event = null;
        }
      });

      this.$watch('tab', (value) => {
        this.fetchIfNeeded(value);
      });

      if (this.event) {
        this.fetchIfNeeded(this.tab);
      }
    },

    switchEvent(ev, updateUrl = true) {
      if (!ev || (this.event && this.event.id === ev.id)) return;

      this.isTransitioning = true;

      setTimeout(() => {
        this.event = ev;

        if (updateUrl) {
          history.pushState({}, '', `/events?event_id=${ev.id}`);
        }

        this.tab = 'peserta';
        this.loadedTabs = {};
        this.dataPeserta = [];
        this.dataLeaderboard = [];
        this.dataDonatur = [];
        this.error = { peserta: null, leaderboard: null, donatur: null };
        this.participantPage = 1;
        this.participantQuery = '';

        this.fetchIfNeeded('peserta');

        this.isTransitioning = false;
      }, 300);
    },

    async fetchIfNeeded(tabName) {
      if (!this.event || this.loadedTabs[tabName]) return;

      const endpoints = {
        peserta: `/api/v1/events/${this.event.id}/teams`,
        leaderboard: `/api/v1/leaderboard?event_id=${this.event.id}`,
        donatur: `/api/v1/events/${this.event.id}/donors`
      };

      const dataMap = {
        peserta: 'dataPeserta',
        leaderboard: 'dataLeaderboard',
        donatur: 'dataDonatur'
      };

       try {
         this.loading[tabName] = true;
         this.error[tabName] = null;

         const res = await fetch(endpoints[tabName]);
         const result = await res.json();
         if (!res.ok || !result.success) throw new Error(result.message || 'Gagal memuat data');

         // Handle different API response shapes:
         // - teams: { data: [...array...] }
         // - leaderboard/donatur: { data: { entries: [...array...] } }
         if (Array.isArray(result.data)) {
           this[dataMap[tabName]] = result.data;
         } else if (result.data && Array.isArray(result.data.entries)) {
           this[dataMap[tabName]] = result.data.entries;
         } else {
           this[dataMap[tabName]] = [];
         }
          this.loadedTabs[tabName] = true;

          if (tabName === 'peserta') {
            const maxPage = Math.ceil(
              this.filteredParticipants.length / this.participantsPerPage
            );

            if (maxPage === 0) {
              this.participantPage = 1;
            } else if (this.participantPage > maxPage) {
              this.participantPage = maxPage;
            }
          }
        } catch(e) {
         this.error[tabName] = 'Gagal memuat data';
         console.error(`Failed to load ${tabName}:`, e);
       } finally {
         this.loading[tabName] = false;
       }
    },

    initials(name) {
      return (name || '?').trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
    },

    formatDate(value) {
      if (!value) return '';
      return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
    },

    get filteredEvents() {
      const query = this.eventQuery.trim().toLocaleLowerCase('id-ID');
      return this.allEvents.filter(event => (!this.openOnly || event.is_voting_open) &&
        `${event.name} ${event.description || ''}`.toLocaleLowerCase('id-ID').includes(query));
    },

    get filteredParticipants() {
      const query = this.participantQuery.trim().toLocaleLowerCase('id-ID');
      return this.dataPeserta.filter(team => `${team.name} ${team.school || ''}`.toLocaleLowerCase('id-ID').includes(query));
    },

    get currentData() {
      return {
        peserta: this.dataPeserta,
        leaderboard: this.dataLeaderboard,
        donatur: this.dataDonatur
      }[this.tab];
    },

    get podiumData() {
      return (this.currentData || []).slice(0, 3);
    },

    get rankingData() {
      return (this.currentData || []).slice(3);
    },

    activeClass(tabName) {
      if (this.tab === tabName) {
        return 'bg-white text-blue-600 font-semibold shadow-md';
      }
      return 'text-slate-500 hover:text-slate-700';
    },

    formatCurrency(amount) {
      return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
      }).format(amount || 0);
    },

    get paginatedParticipants() {
      const start =
          (this.participantPage - 1) * this.participantsPerPage;

      return this.filteredParticipants.slice(
          start,
          start + this.participantsPerPage
      );
    },

    get participantDisplayStart() {
      if (!this.filteredParticipants.length) return 0;

      return (this.participantPage - 1) * this.participantsPerPage + 1;
    },

    get participantDisplayEnd() {
      return Math.min(
          this.participantPage * this.participantsPerPage,
          this.filteredParticipants.length
      );
    },

    get participantTotalPages() {
      return Math.ceil(
          this.filteredParticipants.length / this.participantsPerPage
      );
    },

    nextParticipantPage() {
      if (this.participantPage < this.participantTotalPages) {
        this.participantPage++;
      }
    },

    prevParticipantPage() {
      if (this.participantPage > 1) {
        this.participantPage--;
      }
    },

    goToParticipantPage(page) {
      if (
          page >= 1 &&
          page <= this.participantTotalPages
      ) {
        this.participantPage = page;
      }
    },
  };
}
