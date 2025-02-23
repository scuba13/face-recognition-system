import streamlit as st
from linha.db.handler import MongoDBHandler
from linha.db.crud.employee import EmployeeCRUD
from linha.frontend.pages.employee import render_employee_page
from linha.frontend.pages.monitoring import render_monitoring_page
from linha.core.face_processor import FaceProcessor
from linha.core.image_capture import ImageCapture
from linha.config.settings import PRODUCTION_LINES, CAPTURE_INTERVAL
from linha.core.instance import check_backend_status
from linha.frontend.api_client import APIClient

# Configurações globais do Streamlit
st.set_page_config(
    page_title="LineGuard",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos modernos e ocultação completa de elementos
st.markdown("""
    <style>
        /* Esconder TODOS os elementos do menu superior */
        #MainMenu {visibility: hidden !important;}
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        div[data-testid="stToolbar"] {visibility: hidden !important;}
        div[data-testid="stDecoration"] {visibility: hidden !important;}
        div[data-testid="stStatusWidget"] {visibility: hidden !important;}
        section[data-testid="stSidebar"] > div {padding-top: 0rem !important;}
        section[data-testid="stSidebar"] > div > div {padding-top: 0rem !important;}
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > div:first-child {padding-top: 0rem !important;}
        .stApp > header {display: none !important;}
        .stApp [data-testid="stHeader"] {display: none !important;}
        .stApp [data-testid="stToolbar"] {display: none !important;}
        .stApp [data-testid="stAppViewContainer"] > section:first-child {top: 0 !important;}
        .stApp [data-testid="stSidebarNav"] {display: none !important;}
        .stApp [data-testid="stSidebarNavItems"] {display: none !important;}
        
        /* Remover rolagem e padding */
        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
            overflow: hidden !important;
        }
        
        /* Ajustes da sidebar */
        [data-testid="stSidebar"] {
            background-color: #0E1117;
            width: 200px !important;
        }
        
        /* Estilo dos botões do menu */
        .stButton button {
            width: 100%;
            border: none !important;
            padding: 0.75rem 1rem !important;
            background-color: transparent !important;
            color: #E0E0E0 !important;
            text-align: left !important;
            font-size: 0.95rem !important;
        }
        .stButton button:hover {
            background-color: #2E2E2E !important;
        }
        .stButton button[kind="primary"] {
            background-color: #2E2E2E !important;
            border-radius: 0 !important;
        }
        
        /* Container do logo com gradiente - mantém centralizado */
        .logo-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            width: 100vw;
            background: linear-gradient(135deg, #0E1117 0%, #1E1E1E 100%);
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            margin-left: 100px; /* Compensar a largura da sidebar */
            overflow: hidden;
        }
        
        /* Logo */
        .logo-container img {
            max-width: 450px;
            width: 100%;
            height: auto;
            opacity: 0.85;
            filter: drop-shadow(0 0 15px rgba(255,255,255,0.07));
            position: relative;
            z-index: 1;
            transform: translateX(-50px); /* Ajuste fino para centralizar */
        }
        
        /* Dashboard metrics */
        .dashboard-metrics {
            position: fixed;
            top: 50%;
            right: 2rem;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            padding: 1.5rem;
            z-index: 100;
        }
        
        .metric {
            text-align: left;
            color: #E0E0E0;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .metric-value {
            font-size: 1.2rem;
            font-weight: bold;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
    </style>
""", unsafe_allow_html=True)

class FrontendApp:
    def __init__(self):
        # Inicializar cliente API
        try:
            print("\n=== Iniciando Frontend ===")
            self.api = APIClient()
            
            # Verificar se API está disponível
            status = self.api.health_check()
            if 'error' in status:
                error_msg = status['error']
                print(f"✗ Erro: {error_msg}")
                st.error(f"""
                    Backend não está respondendo!
                    
                    Certifique-se que:
                    1. O backend está rodando (python src/linha/main.py)
                    2. A porta 8000 está disponível
                    3. Não há firewall bloqueando a conexão
                    
                    Erro: {error_msg}
                """)
                st.stop()
                
            print("✓ Conexão com backend estabelecida")
            
            # Inicializar estado da sessão
            if "page" not in st.session_state:
                st.session_state.page = "Início"
            
        except Exception as e:
            print(f"✗ Erro ao inicializar frontend: {str(e)}")
            st.error(f"""
                Erro ao inicializar aplicação!
                
                Erro: {str(e)}
            """)
            st.stop()
        
    def render(self):
        """Renderiza a aplicação"""
        # Menu lateral
        with st.sidebar:
            st.title("LineGuard")
            st.markdown("---")
            
            # Menu de navegação
            pages = ["Início", "Funcionários", "Monitoramento", "Relatórios"]
            
            for page in pages:
                if st.button(
                    page,
                    use_container_width=True,
                    type="primary" if page == st.session_state.page else "secondary"
                ):
                    st.session_state.page = page
                    st.rerun()
        
        # Container principal para conteúdo
        main_container = st.container()
        
        # Limpar container
        main_container.empty()
        
        # Renderizar conteúdo da página selecionada
        with main_container:
            if st.session_state.page == "Início":
                self.show_home()
            elif st.session_state.page == "Funcionários":
                render_employee_page(self.api)
            elif st.session_state.page == "Monitoramento":
                render_monitoring_page(self.api)
            else:
                st.info("🚧 Módulo em desenvolvimento...")
            
    def show_home(self):
        """Página inicial do LineGuard"""
        import os
        
        # Buscar dados do dashboard
        dashboard = self.api.get_dashboard()
        
        # Container principal
        st.markdown("""
            <style>
                .home-container {
                    position: relative;
                    height: 100vh;
                    width: 100%;
                    background: linear-gradient(135deg, #0E1117 0%, #1E1E1E 100%);
                }
            </style>
            <div class="home-container">
        """, unsafe_allow_html=True)
        
        # Logo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "..", "..", "data", "logo", "line_guard1.webp")
        
        if os.path.exists(logo_path):
            # Converter logo
            import base64
            from PIL import Image
            import io
            
            img = Image.open(logo_path)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode()
            
            # Renderizar logo e dashboard
            st.markdown(f"""
                <div class='logo-container'>
                    <img src='data:image/png;base64,{encoded}' alt='LineGuard Logo'>
                </div>
                
                <div class="dashboard-metrics">
                    <div class="metric">
                        <div class="metric-value">👥 {dashboard.get('total_employees', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">📸 {dashboard.get('active_cameras', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{"✅" if dashboard.get('system_status') == "Online" else "❌"} {dashboard.get('system_status', 'Offline')}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Logo não encontrado em: {logo_path}")
        
        # Fechar container
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    # Inicializar app
    app = FrontendApp()
    
    # Renderizar interface
    app.render()

if __name__ == "__main__":
    main() 