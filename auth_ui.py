# auth_ui.py
import streamlit as st
from supabase_client import get_supabase


def render_auth_screen():
    """
    Muestra la pantalla de login/registro.
    Devuelve True si el usuario está autenticado, False si no.
    """

    # Si ya hay sesión activa, no mostrar pantalla de login
    if st.session_state.get("user"):
        return True

    st.markdown(
        """
        <div style='text-align: center; padding: 2rem 0 1rem 0;'>
            <h2 style='color: #333;'>Bienvenida a Lookia 👗</h2>
            <p style='color: #666;'>Inicia sesión o crea tu cuenta para guardar tu closet</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab_login, tab_register = st.tabs(["Iniciar sesión", "Crear cuenta"])

        # ── LOGIN ──────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="tu@email.com")
                password = st.text_input("Contraseña", type="password")
                submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Completa todos los campos.")
                else:
                    try:
                        sb = get_supabase()
                        response = sb.auth.sign_in_with_password({
                            "email": email,
                            "password": password
                        })
                        st.session_state["user"] = response.user
                        st.session_state["access_token"] = response.session.access_token
                        st.rerun()
                    except Exception as e:
                        st.error("Email o contraseña incorrectos.")

        # ── REGISTRO ───────────────────────────────────────
        with tab_register:
            with st.form("register_form"):
                email_reg = st.text_input("Email", placeholder="tu@email.com", key="reg_email")
                password_reg = st.text_input("Contraseña", type="password", key="reg_pass")
                password_reg2 = st.text_input("Repetir contraseña", type="password", key="reg_pass2")
                submitted_reg = st.form_submit_button("Crear cuenta", use_container_width=True)

            if submitted_reg:
                if not email_reg or not password_reg or not password_reg2:
                    st.error("Completa todos los campos.")
                elif password_reg != password_reg2:
                    st.error("Las contraseñas no coinciden.")
                elif len(password_reg) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                else:
                    try:
                        sb = get_supabase()
                        response = sb.auth.sign_up({
                            "email": email_reg,
                            "password": password_reg
                        })
                        if response.user:
                            st.success("¡Cuenta creada! Ya puedes iniciar sesión.")
                        else:
                            st.error("No se pudo crear la cuenta. Intenta de nuevo.")
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")

    return False


def logout():
    try:
        sb = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass
    st.session_state["user"] = None
    st.session_state["access_token"] = None
    st.session_state["wardrobe"] = []
    st.session_state["feedback"] = []
    st.session_state["used_outfits"] = []
    st.rerun()
