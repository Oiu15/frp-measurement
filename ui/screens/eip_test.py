from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivymd.uix.screen import MDScreen


class EipTestScreen(MDScreen):
    conn_text = StringProperty("DISCONNECTED")
    cycle_cnt = NumericProperty(0)
    heartbeat = BooleanProperty(False)
    estop_active = BooleanProperty(False)

    en_local = BooleanProperty(False)
    jog_up = BooleanProperty(False)
    jog_dn = BooleanProperty(False)
    abs1 = BooleanProperty(False)
    abs2 = BooleanProperty(False)

    _ev = None

    def on_pre_enter(self, *args):
        if self._ev is not None:
            self._ev.cancel()
            self._ev = None

        self._ev = Clock.schedule_interval(self._tick, 0.2)  # 5Hz 足够调试

    def on_leave(self, *args):
        if self._ev is not None:
            self._ev.cancel()
            self._ev = None

    def _tick(self, dt):
        app = App.get_running_app()
        plc = getattr(app, "plc_service", None)
        if plc is None:
            self.conn_text = "SERVICE MISSING"
            return

        st = plc.get_latest_state()
        if st is None:
            self.conn_text = "NO DATA"
            return

        self.conn_text = (
            "CONNECTED" if getattr(st, "connected", False) else "DISCONNECTED"
        )

        self.cycle_cnt = int(getattr(st, "cycle_cnt", 0) or 0)
        self.heartbeat = bool(getattr(st, "heartbeat", False))
        self.estop_active = bool(getattr(st, "estop_active", False))

        self.en_local = bool(getattr(st, "en_req_local", False))
        self.jog_up = bool(getattr(st, "jog_up_local", False))
        self.jog_dn = bool(getattr(st, "jog_dn_local", False))
        self.abs1 = bool(getattr(st, "abs1_local", False))
        self.abs2 = bool(getattr(st, "abs2_local", False))
