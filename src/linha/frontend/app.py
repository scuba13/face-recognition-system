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
    page_title="Sistema de Reconhecimento Facial",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Remover TODOS os elementos da UI do Streamlit
st.markdown("""
    <style>
        /* Esconder menu superior, header e footer */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Esconder toolbar e decorações */
        div[data-testid="stToolbar"] {visibility: hidden;}
        div[data-testid="stDecoration"] {visibility: hidden;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
        
        /* Esconder elementos da sidebar */
        section[data-testid="stSidebar"] > div {padding-top: 0rem;}
        section[data-testid="stSidebar"] > div > div {padding-top: 0rem;}
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > div:first-child {padding-top: 0rem;}
        
        /* Esconder outros elementos da UI */
        .stApp > header {display: none;}
        .stApp [data-testid="stHeader"] {display: none;}
        .stApp [data-testid="stToolbar"] {display: none;}
        .stApp [data-testid="stAppViewContainer"] > section:first-child {top: 0;}
        
        /* Esconder navegação da sidebar */
        .stApp [data-testid="stSidebarNav"] {display: none;}
        .stApp [data-testid="stSidebarNavItems"] {display: none;}
        
        /* Ajustar espaçamentos */
        .main .block-container {padding-top: 1rem;}
        
        /* Remover padding superior da sidebar */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding-top: 0rem;
            padding-bottom: 0rem;
        }
        
        /* Esconder qualquer elemento de navegação */
        div.streamlit-expanderHeader {display: none;}
        .sidebar .sidebar-content {padding-top: 0rem;}
        [data-testid="stSidebarNav"] {display: none;}
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
            st.title("Menu Principal")
            st.markdown("---")
            
            # Menu de navegação
            pages = ["Início", "Cadastro de Funcionários", "Monitoramento", "Relatórios"]
            
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
            elif st.session_state.page == "Cadastro de Funcionários":
                render_employee_page(self.api)
            elif st.session_state.page == "Monitoramento":
                render_monitoring_page(self.api)
            else:
                st.info("🚧 Módulo em desenvolvimento...")
            
    def show_home(self):
        """Página inicial"""
        st.title("Sistema de Reconhecimento Facial")
        st.markdown("---")
        
        # Buscar dados do dashboard
        dashboard = self.api.get_dashboard()
        
        if 'error' in dashboard:
            st.error(f"❌ Erro ao carregar dashboard: {dashboard['error']}")
            return
        
        # Cards informativos
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("👥 Funcionários Cadastrados")
            st.metric("Total", dashboard['total_employees'])
            
        with col2:
            st.warning("📸 Câmeras Ativas")
            st.metric("Total", dashboard['active_cameras'])
            
        with col3:
            st.success("✅ Sistema")
            st.metric("Status", dashboard['system_status'])

def main():
    # Inicializar app
    app = FrontendApp()
    
    # Renderizar interface
    app.render()

if __name__ == "__main__":
    main() 