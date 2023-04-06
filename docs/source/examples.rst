Examples
========


.. _example-userutils:

An Example Configuration
------------------------

The following is an example configuration for *Mia! Accounting*.

::

    from flask import Response, redirect
    from .auth import current_user()
    from .modules import User

    def create_app(test_config=None) -> Flask:
        app: Flask = Flask(__name__)

        ... (Configuration of SQLAlchemy, CSRF, Babel_JS, ... etc) ...

        import accounting

        class UserUtils(accounting.UserUtilityInterface[User]):

            def can_view(self) -> bool:
                return True

            def can_edit(self) -> bool:
                return "editor" in current_user().roles

            def can_admin(self) -> bool:
                return current_user().is_admin

            def unauthorized(self) -> Response:
                return redirect("/login")

            @property
            def cls(self) -> t.Type[User]:
                return User

            @property
            def pk_column(self) -> Column:
                return User.id

            @property
            def current_user(self) -> User | None:
                return current_user()

            def get_by_username(self, username: str) -> User | None:
                return User.query.filter(User.username == username).first()

            def get_pk(self, user: User) -> int:
                return user.id

        accounting.init_app(app, UserUtils())

        ... (Any other configuration) ...

        return app
