# Fixture for CPLX-002: PassThroughVariable
# `config` is threaded through 4 functions without being read directly


def handler(request, db, logger, config):
    user = load_user(request, db, config)
    return render(user, logger, config)


def load_user(request, db, config):
    row = fetch(db, request.user_id, config)
    return build_user(row, config)


def fetch(db, user_id, config):
    return db.query(user_id, options=config)


def build_user(row, config):
    return make_user_object(row, config)


def make_user_object(row, config):
    return {"row": row, "options": config}


def render(user, logger, config):
    # `config` actually gets unpacked here -- not a pass-through in this function
    if config.get("verbose"):
        logger.info(user)
    return user
