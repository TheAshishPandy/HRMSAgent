<template>
  <div>
    <div class="row" style="justify-content:space-between">
      <h1>{{ isEmployee ? "Onboarding checklist" : "Onboarding" }}</h1>
      <span v-if="mine && !isEmployee" class="muted">Showing hiring flow</span>
    </div>

    <div v-if="error" class="error" style="margin-bottom:12px">{{ error }}</div>

    <template v-if="isEmployee">
      <div v-if="mine" class="card">
        <div class="row" style="justify-content:space-between;align-items:center">
          <div>
            <h2 style="margin:0">{{ mine.job_title }}</h2>
            <p class="muted" style="margin:4px 0 0">{{ mine.designation }} · {{ mine.department }} · Joins {{ mine.joining_date || "TBD" }}</p>
          </div>
          <span class="pill">{{ mine.status }}</span>
        </div>
        <p style="margin:14px 0 4px">
          <strong>{{ mine.completed_tasks }}/{{ mine.tasks_total }}</strong> tasks complete
        </p>
        <div class="progress"><div class="bar" :style="{ width: pct + '%' }"></div></div>
        <ul class="tasks">
          <li v-for="t in mine.tasks" :key="t.id" :class="{ done: t.completed }">
            <span class="task-title">{{ t.title }}</span>
            <span class="muted task-cat">{{ t.category }}</span>
            <button v-if="mine.status !== 'completed'" type="button" :disabled="t.completed"
              @click="complete(mine, t)">{{ t.completed ? "Done" : "Mark done" }}</button>
            <span v-else class="pill ok">Done</span>
          </li>
        </ul>
        <p v-if="mine.status === 'completed'" class="ok-text">Welcome aboard! Your onboarding is complete.</p>
        <p v-else class="muted" style="margin-bottom:0">Complete every task so People Operations can activate your accounts.</p>
      </div>
      <div v-else-if="checked" class="card">
        <h2 style="margin-top:0">No active onboarding</h2>
        <p class="muted" style="margin-bottom:0">Nothing to do here right now.</p>
      </div>
    </template>

    <template v-else>
      <div class="card">
        <h2 style="margin-top:0">Ready to onboard</h2>
        <div v-if="!eligible.length">
          <p class="muted" style="margin:0">No new hires yet. Accepted offers will appear here once candidates confirm.</p>
        </div>
        <div v-for="c in eligible" :key="c.application_id" class="row" style="justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border,#eee)">
          <div>
            <strong>{{ c.candidate_name }}</strong>
            <p class="muted" style="margin:2px 0 0">{{ c.candidate_email }} · {{ c.job_title }}</p>
          </div>
          <button type="button" @click="pick(c)">Start onboarding</button>
        </div>
      </div>

      <div v-if="showStart && selected" class="card" style="margin-top:16px">
        <h3 style="margin-top:0">Onboard {{ selected.candidate_name }} — {{ selected.job_title }}</h3>
        <div class="grid cols-2">
          <div class="field"><label>Department</label><input v-model="form.department" placeholder="Engineering" /></div>
          <div class="field"><label>Designation</label><input v-model="form.designation" placeholder="Software Engineer" /></div>
          <div class="field"><label>Joining date</label><input v-model="form.joining_date" type="date" /></div>
        </div>
        <p v-if="startError" class="error">{{ startError }}</p>
        <button type="button" :disabled="saving" @click="start">{{ saving ? "Creating…" : "Create employee & checklist" }}</button>
        <button type="button" class="ghost" @click="cancelStart">Cancel</button>
      </div>

      <h2 style="margin-top:24px">Hiring pipeline</h2>
      <div v-if="!records.length" class="card"><p class="muted" style="margin:0">No onboarding records yet. Start one above.</p></div>
      <table v-else class="table">
        <thead>
          <tr><th>Employee</th><th>Role</th><th>Joining</th><th>Progress</th><th>Status</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id">
            <td>
              <strong>{{ r.employee_name }}</strong><br />
              <span class="muted">{{ r.employee_email }}</span>
            </td>
            <td>{{ r.job_title }}<br /><span class="muted">{{ r.designation }}</span></td>
            <td>{{ r.joining_date || "—" }}</td>
            <td>
              <span class="row" style="gap:8px">
                <span class="muted">{{ r.completed_tasks }}/{{ r.tasks_total }}</span>
                <button v-if="r.status !== 'completed' && r.completed_tasks < r.tasks_total" type="button" class="ghost" @click="toggleTasks(r)">Tasks</button>
              </span>
            </td>
            <td><span class="pill">{{ r.status }}</span></td>
          </tr>
        </tbody>
      </table>

      <div v-if="active && active.tasks" class="card" style="margin-top:16px">
        <div class="row" style="justify-content:space-between">
          <h3 style="margin:0">{{ active.employee_name }} — tasks</h3>
          <button type="button" class="ghost" @click="active = null">Close</button>
        </div>
        <ul class="tasks">
          <li v-for="t in active.tasks" :key="t.id" :class="{ done: t.completed }">
            <span class="task-title">{{ t.title }}</span>
            <span class="muted task-cat">{{ t.category }}</span>
            <button v-if="!t.completed" type="button" class="ghost" @click="complete(active, t)">Mark done</button>
            <span v-else class="pill ok">Done</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
<script>
import { api } from "../api";
import { auth } from "../stores/auth";
export default {
  data: () => ({
    records: [],
    eligible: [],
    mine: null,
    checked: false,
    selected: null,
    showStart: false,
    active: null,
    saving: false,
    error: "",
    startError: "",
    form: { department: "", designation: "", joining_date: "" },
  }),
  computed: {
    isEmployee() { return auth.user && auth.user.role === "employee"; },
    pct() {
      if (!this.mine || !this.mine.tasks_total) return 0;
      return Math.round((this.mine.completed_tasks / this.mine.tasks_total) * 100);
    },
  },
  async created() {
    try {
      if (this.isEmployee) {
        try {
          this.mine = await api("/api/onboarding/me");
        } catch (e) {
          if (e.status !== 404) throw e;
        }
        this.checked = true;
      } else {
        const [records, eligible] = await Promise.all([
          api("/api/onboarding"),
          api("/api/onboarding/eligible"),
        ]);
        this.records = records;
        this.eligible = eligible;
      }
    } catch (e) {
      this.error = e.message || "Could not load onboarding";
    }
  },
  methods: {
    pick(c) {
      this.selected = c;
      this.showStart = true;
      this.form = { department: "", designation: "", joining_date: "" };
      this.startError = "";
    },
    cancelStart() {
      this.showStart = false;
      this.selected = null;
    },
    async start() {
      this.saving = true;
      this.startError = "";
      try {
        const rec = await api("/api/onboarding", {
          method: "POST",
          body: JSON.stringify({ application_id: this.selected.application_id, ...this.form }),
        });
        this.records.unshift(rec);
        this.eligible = this.eligible.filter((c) => c.application_id !== this.selected.application_id);
        this.cancelStart();
      } catch (e) {
        this.startError = e.message || "Could not start onboarding";
      } finally {
        this.saving = false;
      }
    },
    toggleTasks(r) {
      this.active = this.active && this.active.id === r.id ? null : r;
    },
    async complete(owner, t) {
      try {
        const updated = await api(`/api/onboarding/tasks/${t.id}/complete`, { method: "POST" });
        if (this.mine && this.mine.id === owner.id) this.mine = updated;
        const idx = this.records.findIndex((r) => r.id === owner.id);
        if (idx >= 0) this.records[idx] = updated;
        if (this.active && this.active.id === owner.id) this.active = updated;
      } catch (e) {
        this.error = e.message || "Could not update task";
      }
    },
  },
};
</script>
<style scoped>
.progress { height: 8px; background: rgba(127,127,127,0.15); border-radius: 999px; overflow: hidden; }
.bar { height: 100%; background: var(--primary, #2563eb); transition: width 0.25s; }
.tasks { list-style: none; padding: 0; margin: 10px 0 0; }
.tasks li { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border, #eee); }
.tasks li.done { opacity: 0.6; }
.task-title { flex: 1; }
.task-cat { text-transform: capitalize; font-size: 12px; }
.pill.ok { background: rgba(34,197,94,0.15); color: #15803d; }
.ok-text { color: #15803d; }
</style>
