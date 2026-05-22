# main.py
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("sobes")


def cmd_prepare(args):
    from sobes_core.config import Config
    from sobes_core.storage import SqliteStore
    from sobes_modules.preparation.service import PreparationService

    cfg = Config()
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    svc = PreparationService(cfg, store)

    profile = svc.create_session_profile(
        company=args.company,
        role=args.role,
        interview_type=args.type,
    )
    logger.info(f"Session created: {profile['id']}")

    if args.scripts_file:
        import json
        with open(args.scripts_file, "r", encoding="utf-8") as f:
            scripts = json.load(f)
        for s in scripts:
            sid = svc.add_script(
                session_id=profile["id"],
                title=s["title"],
                content=s["content"],
                tags=s.get("tags", []),
            )
            logger.info(f"Script added: {s['title']} (id={sid})")

    svc.index_scripts(profile["id"])
    report = svc.get_readiness_report(profile["id"])
    logger.info(f"Readiness: {report['status']}, scripts: {report['scripts_count']}")
    print(f"Session ready: {profile['id']} ({args.company} — {args.role} [{args.type}])")
    return 0


def cmd_start(args):
    from sobes_core.config import Config
    from sobes_core.session_manager import SessionManager

    cfg = Config()
    mgr = SessionManager(pub_port=cfg.zmq_session_port, pull_port=cfg.zmq_session_port + 1)
    logger.info(f"Starting session manager on PUB={cfg.zmq_session_port}")
    mgr.run()
    return 0


def cmd_report(args):
    from sobes_core.config import Config
    from sobes_core.storage import SqliteStore

    cfg = Config()
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()

    if args.session_id:
        session = store.get_session(int(args.session_id))
        if session:
            print(f"Company: {session.company}")
            print(f"Role: {session.role}")
            print(f"Type: {session.interview_type}")
            print(f"Duration: {session.started_at} — {session.ended_at}")
            print(f"Transcript:\n{session.transcript[:500]}...")
        else:
            print(f"Session {args.session_id} not found")
    elif args.list:
        sessions = store.list_sessions(company=args.company)
        for s in sessions:
            print(f"[{s.id}] {s.company} — {s.role} ({s.interview_type}) {s.started_at}")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="sobes", description="Interview Assistant")
    sub = parser.add_subparsers(dest="command")

    p_prepare = sub.add_parser("prepare", help="Create interview session and add scripts")
    p_prepare.add_argument("--company", required=True)
    p_prepare.add_argument("--role", required=True)
    p_prepare.add_argument("--type", required=True, choices=["tech", "hr", "final", "other"])
    p_prepare.add_argument("--scripts-file", help="JSON file with script objects")

    p_start = sub.add_parser("start", help="Start live session (session manager)")

    p_report = sub.add_parser("report", help="View session reports")
    p_report.add_argument("--session-id", type=int)
    p_report.add_argument("--list", action="store_true")
    p_report.add_argument("--company")

    args = parser.parse_args()
    if args.command == "prepare":
        return cmd_prepare(args)
    elif args.command == "start":
        return cmd_start(args)
    elif args.command == "report":
        return cmd_report(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
