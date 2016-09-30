import signal

from pulsar.utils import autoreload
from pulsar import system


class ProcessMixin:

    def is_process(self):
        return True

    def before_start(self, actor):  # pragma    nocover
        actor.start_coverage()
        self._install_signals(actor)
        if actor.cfg.reload:
            autoreload.start()

    def handle_int(self, actor, sig):
        actor.logger.warning("got %s - stopping", system.SIG_NAMES.get(sig))
        self.stop(actor, exit_code=int(sig))

    handle_term = handle_int
    handle_quit = handle_int
    handle_abrt = handle_int

    def handle_winch(self, actor, sig):
        actor.logger.debug("ignore %s", system.SIG_NAMES.get(sig))

    def _install_signals(self, actor):
        proc_name = actor.cfg.proc_name
        if proc_name:
            if not self.is_arbiter():
                name = actor.name.split('.')[0]
                proc_name = "%s-%s" % (proc_name, name)
            if system.set_proctitle(proc_name):
                actor.logger.debug('Set process title to %s',
                                   system.get_proctitle())
        system.set_owner_process(actor.cfg.uid, actor.cfg.gid)
        actor.logger.debug('Installing signals')
        loop = actor._loop
        for sig in system.SIGNALS:
            name = system.SIG_NAMES.get(sig)
            if name:
                handler = getattr(self, 'handle_%s' % name.lower(), None)
                if handler:
                    loop.add_signal_handler(sig, handler, actor, sig)

    def _remove_signals(self, actor):
        actor.logger.debug('Remove signal handlers')
        for sig in system.SIGNALS:
            try:
                actor._loop.remove_signal_handler(sig)
            except Exception:
                pass
        if actor._loop.is_running():  # pragma nocover
            actor.logger.critical('Event loop still running when stopping')
            actor._loop.stop()
        else:
            actor.logger.debug('Close event loop')
            actor._loop.close()


def signal_from_exitcode(sig):
    if sig in QUIT:
        sig = signal.SIGQUIT
    return sig


QUIT = set((signal.SIGINT, signal.SIGQUIT))