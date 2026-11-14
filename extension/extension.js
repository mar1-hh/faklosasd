const {St, Clutter, Gio, GLib} = imports.gi;
const Main = imports.ui.main;
const PanelMenu = imports.ui.panelMenu;
const PopupMenu = imports.ui.popupMenu;
const Me = imports.misc.extensionUtils.getCurrentExtension();
const ByteArray = imports.byteArray;

class NeonDesktop {
    enable() {
        this.alive = true;
        this.root = GLib.path_get_dirname(Me.path);
        // The installer places a small paths file inside the installed extension.
        try { this.root = JSON.parse(ByteArray.toString(GLib.file_get_contents(Me.path + '/paths.json')[1])).root; } catch (e) {}
        this.cards = [];
        this.sources = [];
        this.processes = new Set();
        this.build();
        this.monitorSignal = Main.layoutManager.connect('monitors-changed', () => this.position());
        this.tick();
        this.sources.push(GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {this.tick(); return GLib.SOURCE_CONTINUE;}));
        this.refresh();
        this.sources.push(GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 300, () => {this.refresh(); return GLib.SOURCE_CONTINUE;}));
    }
    card(title, width) {
        let c = new St.BoxLayout({vertical: true, style_class: 'neon-card', width});
        if (title) c.add_child(new St.Label({text: title, style_class: 'neon-heading'}));
        Main.layoutManager._backgroundGroup.add_child(c);
        this.cards.push(c);
        return c;
    }
    label(parent, text, style = '') {
        let l = new St.Label({text, style_class: style}); parent.add_child(l); return l;
    }
    button(parent, text, action) {
        let b = new St.Button({label:text, style_class:'neon-action', reactive:true, can_focus:true});
        b.connect('clicked', action); parent.add_child(b); return b;
    }
    launch(uri) { Gio.AppInfo.launch_default_for_uri(uri, global.create_app_launch_context(0,-1)); }
    build() {
        this.logCard = this.card('42  /  LOGTIME', 232);
        this.hours = this.label(this.logCard, 'Loading…', 'neon-hours');
        this.progress = this.label(this.logCard, '────────────', 'neon-small');
        this.period = this.label(this.logCard, '28th → 27th', 'neon-small');
        this.detail = this.label(this.logCard, 'Target · 120 hours', 'neon-small');
        this.status = this.label(this.logCard, 'Fetching your logtime', 'neon-small');
        this.button(this.logCard, 'Refresh', () => this.refresh());
        this.links = this.card('QUICK LINKS', 232);
        this.button(this.links, '42 Intra ↗', () => this.launch('https://profile.intra.42.fr/'));
        this.button(this.links, 'GitHub ↗', () => this.launch('https://github.com/'));
        this.clockCard = this.card('', 300);
        this.clock = this.label(this.clockCard, '00:00', 'neon-clock');
        this.date = this.label(this.clockCard, '', 'neon-small');
        this.system = this.card('SYSTEM', 240);
        this.stats = this.label(this.system, 'Memory …\n\nCPU …');
        this.calendar = this.card('CALENDAR', 240);
        this.calendarText = this.label(this.calendar, '');
        this.notes = this.card('FOCUS', 240);
        this.label(this.notes, 'Make something meaningful.\nOne session at a time.', 'neon-small');
        this.dock = this.card('', 430);
        this.dock.vertical = false;
        let apps = imports.gi.Shell.AppSystem.get_default();
        for (let [id, title] of [['firefox.desktop','Web'],['org.gnome.Nautilus.desktop','Files'],['org.gnome.Terminal.desktop','Terminal'],['code.desktop','Code']]) {
            let app = apps.lookup_app(id);
            if (app) { let b = new St.Button({child:app.create_icon_texture(32), style_class:'neon-action', accessible_name:title}); b.connect('clicked', () => app.activate()); this.dock.add_child(b); }
        }
        this.button(this.dock, 'Apps', () => Main.overview.show());
        this.indicator = new PanelMenu.Button(0.0, 'Neon Desktop');
        this.indicator.add_child(new St.Label({text:'◈', y_align:Clutter.ActorAlign.CENTER}));
        Main.panel.addToStatusArea('neon-desktop', this.indicator);
        this.indicator.menu.addAction('Refresh logtime', () => this.refresh());
        this.indicator.menu.addAction('Show / hide desktop cards', () => { for (let c of this.cards) c.visible = !c.visible; });
        this.indicator.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        let folder = Gio.File.new_for_path(this.root + '/wallpapers');
        let enumerator = folder.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
        let entry;
        let names = [];
        while ((entry = enumerator.next_file(null))) if (entry.get_name().endsWith('.png')) names.push(entry.get_name());
        enumerator.close(null);
        let backgroundSettings = new Gio.Settings({schema_id:'org.gnome.desktop.background'});
        let wallpaperWritable = backgroundSettings.is_writable('picture-uri') && backgroundSettings.is_writable('picture-uri-dark');
        if (!wallpaperWritable) {
            let locked = new PopupMenu.PopupMenuItem('Wallpapers locked by administrator', {reactive:false});
            this.indicator.menu.addMenuItem(locked);
        }
        for (let name of (wallpaperWritable ? names.sort() : [])) this.indicator.menu.addAction(name.replace('.png','').replace(/-/g,' '), () => {
            let settings = new Gio.Settings({schema_id:'org.gnome.desktop.background'});
            let uri = Gio.File.new_for_path(this.root + '/wallpapers/' + name).get_uri();
            settings.set_string('picture-uri', uri); settings.set_string('picture-uri-dark', uri); settings.set_string('picture-options','zoom');
        });
        this.position();
    }
    position() {
        let m = Main.layoutManager.primaryMonitor;
        if (!m) return;
        let pad = 24, top = m.y + Main.panel.height + 22;
        this.logCard.set_position(m.x+pad, top);
        this.links.set_position(m.x+pad, top+380);
        this.clockCard.set_position(m.x+Math.round((m.width-300)/2), top+20);
        this.system.set_position(m.x+m.width-264, top);
        this.calendar.set_position(m.x+m.width-264, top+180);
        this.notes.set_position(m.x+m.width-264, top+430);
        this.dock.set_position(m.x+Math.round((m.width-430)/2), m.y+m.height-95);
        // On smaller displays avoid overlapping the calendar and dock.
        this.notes.visible = m.height >= 850;
    }
    tick() {
        let now = GLib.DateTime.new_now_local();
        this.clock.text = now.format('%H:%M');
        this.date.text = now.format('%A, %d %B');
        let js = new Date();
        let first = new Date(js.getFullYear(), js.getMonth(), 1);
        let count = new Date(js.getFullYear(), js.getMonth()+1, 0).getDate();
        let cells = Array((first.getDay()+6)%7).fill('  ');
        for(let n=1;n<=count;n++) cells.push(String(n).padStart(2,' '));
        let rows=[]; for(let i=0;i<cells.length;i+=7) rows.push(cells.slice(i,i+7).join(' '));
        this.calendarText.text = now.format('%B %Y')+'\n\n'+now.format('%d')+'  /  Today\n\nMo Tu We Th Fr Sa Su\n'+rows.join('\n');
        this.calendarText.set_style('font-family: monospace; font-size: 11px;');
        try {
            let mem=ByteArray.toString(GLib.file_get_contents('/proc/meminfo')[1]);
            let total=Number(mem.match(/MemTotal:\s+(\d+)/)[1]);
            let available=Number(mem.match(/MemAvailable:\s+(\d+)/)[1]);
            let cpu=ByteArray.toString(GLib.file_get_contents('/proc/stat')[1]).split('\n')[0].trim().split(/\s+/).slice(1,9).map(Number);
            let sum=cpu.reduce((a,b)=>a+b,0), idle=cpu[3]+cpu[4];
            let use=this.prevCpu && sum>this.prevCpu[0] ? Math.round(100*(1-(idle-this.prevCpu[1])/(sum-this.prevCpu[0]))) : null;
            this.prevCpu=[sum,idle];
            this.stats.text = `Memory     ${Math.round(100*(1-available/total))}%\n\nCPU        ${use===null?'…':use+'%'}`;
        } catch(e) { this.stats.text='System readings unavailable'; }
    }
    refresh() {
        if (this.busy) return;
        this.busy = true;
        this.status.text='Refreshing…';
        let proc;
        try {
            proc = Gio.Subprocess.new([this.root+'/python', this.root+'/logtime-widget.py'], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            this.processes.add(proc);
            proc.communicate_utf8_async(null, null, (p,res) => {
                this.processes.delete(p); this.busy=false;
                if (!this.alive) return;
                try {
                    let [,out,err] = p.communicate_utf8_finish(res);
                    if (!p.get_successful()) throw Error(err);
                    let data=JSON.parse(out), h=data.hours;
                    this.hours.text=Number(h.projected).toFixed(1)+' h';
                    let filled=Math.max(0,Math.min(12,Math.round(12*h.projected/h.target)));
                    this.progress.text='━'.repeat(filled)+'─'.repeat(12-filled)+'  '+Math.round(h.projected/h.target*100)+'%';
                    this.period.text=data.period.start+' → '+data.period.end;
                    this.detail.text=`Target · ${h.target} h   /   Today · ${(h.today+h.session).toFixed(1)} h`;
                    this.status.text='Includes active session';
                } catch(e) { this.status.text='Unavailable · try Refresh'; }
            });
        } catch(e) { this.busy=false; this.status.text='Python unavailable · see README'; }
    }
    disable() {
        this.alive=false;
        for(let source of this.sources) GLib.source_remove(source);
        for(let proc of this.processes) proc.force_exit();
        Main.layoutManager.disconnect(this.monitorSignal);
        for(let card of this.cards) card.destroy();
        this.indicator.destroy();
    }
}
function init() { return new NeonDesktop(); }
