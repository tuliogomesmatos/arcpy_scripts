# =============================================================================
# SCRIPT FINAL COMPLETO
# ArcGIS 10.8 / ArcPy + PIL
#
# Para cada grupo gera 4 PNGs salvos em DUAS pastas:
#   - C:\...\por feicao\GRUPO\        (junto com os shapes)
#   - C:\...\mapas_finais\GRUPO\      (só imagens)
#
# PNG 1 — Litologia + Sedes          | zoom grupo
# PNG 2 — Litologia + limite_TO      | zoom estado inteiro
# PNG 3 — Raster K RGB (sem recorte) | zoom grupo | fundo branco
# PNG 4 — Legenda da litologia       | cores exatas do .lyr
#
# COMO RODAR:
#   Geoprocessing > Python Window
#   execfile(r"C:\Tulio\Projeto de pesquisa\por feicao\script_final.py")
# =============================================================================

import arcpy
import arcpy.mapping as mapping
import os
import shutil

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    try:
        import Image, ImageDraw, ImageFont
    except ImportError:
        import subprocess, sys
        subprocess.call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
        from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

K_RASTER      = r"C:\Tulio\Projeto de pesquisa\FigGeofTocantins\FigGeofTocantins\Gama\K.tif"
K_LYR         = r"C:\Tulio\Projeto de pesquisa\shape\K_CORR.tif.lyr"
MXD_BASE      = r"C:\Tulio\Projeto de pesquisa\shape\Untitled.mxd"
LITO_LYR      = r"C:\Tulio\Projeto de pesquisa\por feicao\R18Litologia_Integrada_final2022_12_22.lyr"
PASTA_SHAPES  = r"C:\Tulio\Projeto de pesquisa\por feicao"       # pasta com shapes
PASTA_FINAL   = r"C:\Tulio\Projeto de pesquisa\mapas_finais"     # pasta só imagens

NOME_LAYER_TO    = "limite_TO"
NOME_LAYER_SEDES = "Sedes"

# Mapas A4 retrato 300 DPI
DPI        = 300
LARGURA_PX = 2480
ALTURA_PX  = 3508
MARGEM_PCT = 0.08

# Legenda PIL
LEG_LARGURA   = 2000
LEG_CAIXA_W   = 80
LEG_CAIXA_H   = 50
LEG_ESPACO    = 12
LEG_MARGEM    = 60
LEG_FONTE_TIT = 52
LEG_FONTE_ITM = 36
COR_FUNDO     = (255, 255, 255)
COR_TEXTO     = (0, 0, 0)
COR_BORDA     = (180, 180, 180)

# =============================================================================
# GRUPOS E SIGLAS
# =============================================================================

GRUPOS = {
    "COMPLEXO RIO DOS MANGUES": [
        "PP2rmma","PP2rmnr","PP2rmnrc","PP2rmnrqz","PP2rmnrx","PP2_alfa_rmma"],
    "COMPLEXO OFIOLITICO QUATIPURU": [
        "NP1_mu_q","NP1_mu_qbif","NP1_mu_qp","NP1_mu_qvs"],
    "SUITE MONTE SANTO E SERRA DA ESTRELA": [
        "MP3_lambda_ms","MP3_lambda_e"],
    "COMPLEXO PORANGATU": [
        "NP3por1","NP3por2","NP3por2vqz","NP3por3","NP3por3a","NP3poradk"],
    "SUITE LAJEADO": [
        "NP3_gamma_la","NP3_gamma_mt","NP3_gamma_mth",
        "NP3_gamma_pl","NP3_gamma_plh","NP3_delta_lgb"],
    "SUITE MATA AZUL": [
        "NP3_gamma_ma1","NP3_gamma_ma2","NP3_gamma_ma3"],
    "SUITE ALCALINA DO PEIXE": [
        "MP1_lambda_p","MP1_lambda_pl"],
    "GRUPO SERRA DA MESA": [
        "MP1sm","MP1smcc","MP1smmm","MP1smqt",
        "MP1tr","MP1trc","MP1trq","MP1trx"],
    "COMPLEXO ALMAS CAVALCANTE": [
        "PP12_delta_acqd","PP12_gamma_acg","PP12_gamma_acgm","PP12_gamma_acgp"],
    "FORMACAO MONTE DO CARMO": [
        "NP3mca","NP3mcacg","NP3_alfa_mcaa","NP3_alfa_mcad"],
    "FORMACAO SANTA ROSA": [
        "PP2_alfa_sr"],
    "SUITE AURUMINA": [
        "PP2_gamma_au1","PP2_gamma_au2","PP2_gamma_au3","PP2_gamma_au4"],
    "SUITE RIBEIRAO DAS ALDEIAS": [
        "PP12_gamma_acg","PP12_gamma_acgp"],
    "FORMACAO XAMBIOA": [
        "NP3x","NP3xcc"],
    "FORMACAO MOSQUITO": [
        "T3J1_beta_m"],
    "FORMACAO COUTO MAGALHAES": [
        "NP23ct","NP23ctarn","NP23ctca"],
    "GRUPO SERRA DA MESA CARBONATICAS": [
        "MP1sm","MP1smcc","MP1smmm","MP1smqt",
        "MP1tr","MP1trc","MP1trq","MP1trx"],
    "GRUPO NATIVIDADE": [
        "PP4nat1","PP4nat1ci","PP4nat1do","PP4nat2","PP4nat2cc","PP4nat2qt",
        "PP4nat3","PP4nat3do","PP4nat3qt","PP4nat4","PP4nat5","PP4nat6",
        "PP4nat6do","PP4nat7","PP4nat8"],
    "BAMBUI SETE LAGOAS": ["NP3slc"],
    "BAMBUI LAGOA DO JACARE": ["NP3lj"],
    "BAMBUI SERRA SANTA HELENA": ["NP3bsh","NP3shp"],
    "GRUPO ARAI FORMACAO ARRAIAS": [
        "PP4a_alfa","PP4acg","PP4aqa","PP4aqo"],
    "BALSAS MOTUCA": ["P3m"],
    "BALSAS PEDRA DE FOGO": ["P12pf"],
}

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def nf(grupo):
    return grupo.replace(" ", "_").replace("-", "_")

def criar_pasta(path):
    if not os.path.exists(path):
        os.makedirs(path)

def encontrar_shp(pasta):
    for f in os.listdir(pasta):
        if f.lower().startswith("lito_") and f.lower().endswith(".shp"):
            return os.path.join(pasta, f)
    return None

def zoom_grupo(df, layer):
    desc = arcpy.Describe(layer)
    ext  = desc.extent
    dx   = (ext.XMax - ext.XMin) * MARGEM_PCT
    dy   = (ext.YMax - ext.YMin) * MARGEM_PCT
    df.extent = arcpy.Extent(
        ext.XMin - dx, ext.YMin - dy,
        ext.XMax + dx, ext.YMax + dy
    )

def exportar_png(mxd, caminho):
    mapping.ExportToPNG(
        mxd, caminho,
        resolution=DPI,
        df_export_width=LARGURA_PX,
        df_export_height=ALTURA_PX
    )
    print("    >> {}".format(os.path.basename(caminho)))

def salvar_nas_duas_pastas(src, pasta_shapes_grupo, pasta_final_grupo):
    """Copia o PNG gerado para a pasta final (já está na de shapes)."""
    dst = os.path.join(pasta_final_grupo, os.path.basename(src))
    shutil.copy2(src, dst)

# =============================================================================
# LÊ CORES DO .LYR
# =============================================================================

NOMES_SIGLA = {
    u'A34sag': u'Serra Azul de Goiás',
    u'A3co': u'Colmeia',
    u'C1po': u'Poti',
    u'C2pi': u'Piauí',
    u'C_cortado_1_delta_mm': u'Acamadada Morro da Mata',
    u'C_cortado_1_delta_rc': u'Acamadado Rio Crixás',
    u'C_cortado_1_gamma_slbr': u'Granito Barrolândia',
    u'D1i': u'Itaim',
    u'D23c': u'Cabeças',
    u'D23p': u'Pimenteira',
    u'D3C1l': u'Longá',
    u'J3K1c': u'Corda',
    u'K12it': u'Itapecuru',
    u'K1c': u'Codó',
    u'K2up': u'Posse',
    u'K2usa': u'Serra das Araras de Minas Gerais',
    u'K2usacg': u'Serra das Araras de Minas Gerais, conglomerado',
    u'MP1_lambda_p': u'Alcalina de Peixe',
    u'MP1_lambda_pl': u'Alcalina de Peixe, lichtfieldito',
    u'MP1sm': u'Serra da Mesa',
    u'MP1smcc': u'Serra da Mesa, calcixisto e calcissilicática',
    u'MP1smmm': u'Serra da Mesa, metamarga e mármore',
    u'MP1smqt': u'Serra da Mesa, quartzito',
    u'MP1tr': u'Traíras',
    u'MP1trc': u'Traíras, calcário',
    u'MP1trq': u'Traíras, quartzito',
    u'MP1trx': u'Traíras, xisto',
    u'MP2cp1': u'Palmeirópolis, rudácea',
    u'MP2cp1gv': u'Palmeirópolis - Rudácea - litofácies Grauvaca',
    u'MP2cp1vc': u'Palmeirópolis - Rudácea - litofácies vulcanoclástica',
    u'MP2cp2': u'Palmeirópolis, anfibolítica 2',
    u'MP2cp3': u'Palmeirópolis, metavulcanossedimentar básica',
    u'MP2cp3xt': u'Palmeirópolis - Vulcanossedimentar Básica - litofácies xisto',
    u'MP2cp4': u'Palmeirópolis, metavulcanossedimentar ácida',
    u'MP2cp4a': u'Palmeirópolis - Vulcanossedimentar Ácida - litofácies anfibolito',
    u'MP2cp4vxt1': u'Palmeirópolis - Vulcanossedimentar Ácida - metavulcânica riodacítica a dacítica',
    u'MP2cp4vxt2': u'Palmeirópolis - Vulcanossedimentar Ácida - metavulcânica riolítica a riodacítica',
    u'MP2cp4vxt3': u'Palmeirópolis - Vulcanossedimentar Ácida - metavulcânica riolítica',
    u'MP3_lambda_e': u'Serra da Estrela',
    u'MP3_lambda_ms': u'Monte Santo',
    u'MPpa3': u'Paranoá 3, rítmica quartzítica intermediária',
    u'MPpa4': u'Grupo Paranoá - Unidade Rítmica Pelito-carbonatada',
    u'MPpa4cc': u'Grupo Paranoá - Unidade Rítmica Pelito-carbonatada - Metacalcário',
    u'MPpa4qt': u'Grupo Paranoá - Unidade Rítmica Pelito-carbonatada - Quartzito',
    u'N1dl': u'Cobertura detrito-lateritica ferruginosa',
    u'NP12jt': u'Jequitaí',
    u'NP1_delta_x': u'Suíte Xambica',
    u'NP1_gamma_mr': u'Granito Morro Solto',
    u'NP1_mu_cmi': u'Complexo Canabrava - Unidade Máfica Inferior',
    u'NP1_mu_cu': u'Complexo Canabrava - Unidade Ultramáfica',
    u'NP1_mu_q': u'Complexo Ofiolítico Quatipuru',
    u'NP1_mu_qbif': u'Complexo Ofiolítico Quatipuru - Litofácies Formação Ferrífera',
    u'NP1_mu_qp': u'Complexo Ofiolítico Quatipuru - Plutônica',
    u'NP1_mu_qvs': u'Complexo Ofiolítico Quatipuru - Unidade Vulcanossedimentar',
    u'NP1mra': u'Complexo Mara Rosa - Unidade Anfibolito',
    u'NP1mro': u'Complexo Mara Rosa',
    u'NP23ct': u'Couto Magalhães',
    u'NP23ctarn': u'Couto Magalhães - Litofácies Arenito Lítico',
    u'NP23ctca': u'Couto Magalhães - Litofácies Calcário',
    u'NP23cv': u'Canto da Vazante',
    u'NP3_C_cortado_1_gamma_sl': u'Santa Luzia',
    u'NP3_C_cortado_1_gamma_slg': u'Granito Santa Luzia',
    u'NP3_C_cortado_1_gamma_slpeg': u'Santa Luzia - Granito Santa Luzia - Litofácies Pegmatito',
    u'NP3_alfa_mcaa': u'Monte do Carmo - Fácies Vulcânica - Litofácies Andesito',
    u'NP3_alfa_mcad': u'Monte do Carmo - Fácies Vulcânica - Litofácies Metadacito',
    u'NP3_alfa_st': u'Santa Tereza - Litofácies Vulcânicas ácidas',
    u'NP3_delta_lgb': u'Lajeado - Granito Lajeado - Litofácies Gabronorito',
    u'NP3_delta_re': u'Rio Crixás - Corpo Rio Escuro',
    u'NP3_gamma_ars': u'Granito Aroeira',
    u'NP3_gamma_at': u'Aliança do Tocantins - Corpo Aliança do Tocantins',
    u'NP3_gamma_la': u'Granito Lajeado',
    u'NP3_gamma_ma1': u'Suíte Mata Azul - Litofácies granito e sienogranito',
    u'NP3_gamma_ma2': u'Suíte Mata Azul - Litofácies granitos aluminosos',
    u'NP3_gamma_ma3': u'Suíte Mata Azul - Litofácies granito',
    u'NP3_gamma_mt': u'Lajeado - Granito Matança',
    u'NP3_gamma_mth': u'Lajeado - Granito Matança - Litofácies granito a hiperstênio',
    u'NP3_gamma_pl': u'Granito Palmas',
    u'NP3_gamma_plh': u'Lajeado - Granito Palmas - Litofácies granito a hiperstênio',
    u'NP3_gamma_sjp': u'Granito São José Pequeno',
    u'NP3_gamma_slcl1': u'Santa Luzia - Granito Córrego das Lajes - Biotita sienogranito',
    u'NP3_gamma_slcl2': u'Suite Santa Luzia - Granito Córrego das Lajes - Biotita sienogranito potássico',
    u'NP3_gamma_slk': u'Santa Luzia - Granito Presidente Kennedy',
    u'NP3_gamma_slr': u'Santa Luzia - Granito Ramal do Lontra',
    u'NP3_gamma_sst': u'Santa Tereza',
    u'NP3bsh': u'Grupo Bambuí - Serra de Santa Helena',
    u'NP3lj': u'Grupo Bambuí - Lagoa do Jacaré',
    u'NP3mca': u'Monte do Carmo',
    u'NP3mcacg': u'Monte do Carmo - Litofácies Conglomerado',
    u'NP3mu': u'Mucambo',
    u'NP3muff': u'Mucambo - Litofácies Formação Ferrífera',
    u'NP3por1': u'Complexo Porangatu - Unidade Granulito',
    u'NP3por2': u'Complexo Porangatu - Unidade Ortognaisse',
    u'NP3por2vqz': u'Complexo Porangatu - Unidade Ortognaisse - Litofácies Veio de Quartzo',
    u'NP3por3': u'Complexo Porangatu - Unidade Anfibolito e Tonalito',
    u'NP3por3a': u'Complexo Porangatu - Unidade Anfiboltio e Tonalito - Litofácies Anfibolito',
    u'NP3poradk': u'Complexo Porangatu - Unidade Adakito',
    u'NP3pq': u'Pequizeiro',
    u'NP3shp': u'Grupo Bambuí - Serra de Santa Helena - Pelitos e marga calcítica',
    u'NP3slc': u'Grupo Bambuí - Subgrupo Paraopeba - Formação Sete Lagoas - Dolomito',
    u'NP3x': u'Xambioá',
    u'NP3xcc': u'Xambioá - Litofácies Metacalcários',
    u'NP_delta_se': u'Gabro Diorítico Serra do Estrondo',
    u'NPmcp': u'Morro do Campo',
    u'Nrb': u'Rio das Barreiras',
    u'Nrbcg': u'Rio das Barreiras - Conglomerado',
    u'P12pf': u'Balsas - Formação Pedra de Fogo',
    u'P3m': u'Balsas - Formação Motuca',
    u'PP12_delta_acqd': u'Complexo Almas-Cavalcante - Unidade anfibolítica a quartzo-diorítica',
    u'PP12_gamma_acg': u'Complexo Almas-Cavalcante - Unidade Granodiorítica a Tonalítica',
    u'PP12_gamma_acgm': u'Complexo Almas-Cavalcante - Unidade Granodiorítica a Tonalítica - Migmatito',
    u'PP12_gamma_acgp': u'Complexo Almas-Cavalcante - Unidade Granodioritica a tonalitica - Peraluminosa',
    u'PP12_gamma_pr': u'Suíte Pau Ramalhudo',
    u'PP1_gamma_ra': u'Suíte Ribeirão das Areias',
    u'PP1_gamma_sp': u'Suíte Serra do Pilão',
    u'PP1cp': u'Grupo Riachão do Ouro - Formação Córrego do Paiol',
    u'PP1ff': u'Sequencia Fazenda Santa Fe',
    u'PP23_gamma_ip': u'Suite Ipueiras',
    u'PP23_gamma_ipa': u'Suíte Ipueiras - Corpo Areias',
    u'PP23_gamma_ipc': u'Suíte Ipueiras - Corpo Monte do Carmo',
    u'PP23_gamma_ipi': u'Suíte Ipueiras - Corpo Italia',
    u'PP23_gamma_ipp': u'Suite Ipueiras - Corpo Ipueiras',
    u'PP2_alfa_rmma': u'Complexo Rio dos Mangues - Unidade Morro do Aquiles - Metavulcanicas',
    u'PP2_alfa_sr': u'Santa Rosa do Tocantins',
    u'PP2_delta_g': u'Máfico-Ultramáfica Barra do Gameleira',
    u'PP2_gamma_au1': u'Suíte Aurumina - Fácies Sienogranítica',
    u'PP2_gamma_au2': u'Suíte Aurumina - Fácies Granodiorítica a Monzogranítica',
    u'PP2_gamma_au3': u'Suíte Aurumina - Fácies Granodiorítica a Tonalítica',
    u'PP2_gamma_au4': u'Suíte Aurumina - Fácies Monzogranítica a Granodiorítica porfirítica a porfiroblástica',
    u'PP2_gamma_pnoa': u'Complexo Porto Nacional - Litofacies Anfibolica',
    u'PP2_gamma_pnog': u'Complexo Porto Nacional - Litofacies Granulitica',
    u'PP2_gamma_sb': u'Serra do Boqueirão',
    u'PP2_gamma_sblt': u'Serra do Boqueirão - Litofácies Leucotonalito',
    u'PP2mc': u'Grupo Riachão do Ouro - Formação Morro do Carneiro',
    u'PP2mccg': u'Grupo Riachão do Ouro - Formação Morro do Carneiro - Fácies Metaconglomerado',
    u'PP2mcqt': u'Grupo Riachão do Ouro - Formação Morro do Carneiro - Fácies Quartzito',
    u'PP2mcsq': u'Grupo Riachão do Ouro - Formação Morro do Carneiro - Fácies Metassedimentar Química',
    u'PP2rmma': u'Complexo Rio dos Mangues - Unidade Morro do Aquiles - Litofacies Peliticas',
    u'PP2rmnr': u'Complexo Rio dos Mangues - Unidade Nova Rosalandia - Litofacies Calcissilicatica',
    u'PP2rmnrc': u'Complexo Rio dos Mangues - Unidade Nova Rosalandia - Litofacies Calcissilicatica - Calcário',
    u'PP2rmnrqz': u'Complexo Rio dos Mangues - Unidade Nova Rosalândia - Quartzitos',
    u'PP2rmnrx': u'Complexo Rio dos Mangues - Unidade Nova Rosalandia - Xisto',
    u'PP2tz': u'Ticunzal',
    u'PP2tzp': u'Formacao Ticunzal - Facies Paragnaisses',
    u'PP2tzqt': u'Formacao Ticunzal - Facies Quartzito',
    u'PP2tzsq': u'Formacao Ticunzal - Facies Metassedimentar Quimica',
    u'PP3_delta_cc': u'Suite Carreira Comprida',
    u'PP3_gamma_ipu': u'Suíte Ipueiras - Corpo Pugmil',
    u'PP3_gamma_sca': u'Gnaisse Cantão',
    u'PP3_gamma_se': u'Suite Serrote',
    u'PP4a_alfa': u'Grupo Araí - Formação Arraias - Litofácies vulcânica',
    u'PP4acg': u'Grupo Araí - Formação Arraias - Litofácies conglomerado',
    u'PP4aqa': u'Grupo Araí - Formação Arraias - Litofácies Quartzito Arcoseano',
    u'PP4aqo': u'Grupo Araí - Formação Arraias - Litofácies ortoquartzitos',
    u'PP4nat1': u'Grupo Natividade - Unidade Metapsamo-psefítica',
    u'PP4nat1ci': u'Grupo Natividade - Unidade Metapsamo-psefítica - Cianita-quartzitos',
    u'PP4nat1do': u'Grupo Natividade - Unidade Metapsamo-psefítica - Metadolomitos',
    u'PP4nat2': u'Grupo Natividade - Unidade Metapelito-psamitica-carbonatada',
    u'PP4nat2cc': u'Grupo Natividade - Unidade Metapelito-psamitica-carbonatada - Metacalcários',
    u'PP4nat2qt': u'Grupo Natividade - Unidade Metapelito-psamitica-carbonatada - Quartzitos',
    u'PP4nat3': u'Grupo Natividade - Unidade Metapsamo-pelitica carbonatada',
    u'PP4nat3do': u'Grupo Natividade - Unidade Metapsamo-pelitica carbonatada - Metadolomitos',
    u'PP4nat3qt': u'Grupo Natividade - Unidade Metapsamo-pelitica carbonatada - Quartzitos',
    u'PP4nat4': u'Grupo Natividade - Unidade Metapsamo-pelítica',
    u'PP4nat5': u'Grupo Natividade - Unidade Metapsamítica',
    u'PP4nat6': u'Grupo Natividade - Unidade Metapelítica carbonatada',
    u'PP4nat6do': u'Grupo Natividade - Unidade Metapelítica carbonatada - Metadolomitos',
    u'PP4nat7': u'Grupo Natividade - Unidade Metarritmitos',
    u'PP4nat8': u'Grupo Natividade - Unidade Metapelito-psamítica',
    u'PPMP_beta_mtv': u'Suíte Granitos da Sub-Provincia Tocantins - Unidade Metavulcânica Máfica',
    u'PPMP_gamma_t': u'Suíte Granitos da Sub-Provincia Tocantins - indiviso',
    u'PPMP_gamma_tsd': u'Suíte Granitos da Sub-Provincia Tocantins - Granito Serra Dourada',
    u'PPMP_gamma_tse': u'Suíte Granitos da Sub-Provincia Tocantins - Granito Serra do Encosto',
    u'Q1a': u'Depósitos aluvionares antigos',
    u'Q2a': u'Depósitos aluvionares',
    u'Q2c': u'Coberturas detrito-lateriticas',
    u'Qag': u'Araguaia',
    u'Qag1': u'Araguaia - Terraços Aluvionares',
    u'SDab': u'Água Bonita',
    u'Ssg': u'Grupo Serra Grande',
    u'Ssgj': u'Grupo Serra Grande - Jaicós',
    u'T3J1_beta_m': u'Mosquito',
    u'Ts': u'Balsas - Formação Sambaíba',
}

def ler_cores_lyr(lyr_path):
    """
    Lê cores do .lyr parseando o XML do renderer diretamente.
    Funciona no ArcGIS 10.8 onde classDescriptions nao expoe as cores.
    """
    import re
    cores = {}
    try:
        lyr = mapping.Layer(lyr_path)
        # Adiciona ao MXD temporariamente para acessar o renderer
        mxd_temp = mapping.MapDocument(MXD_BASE)
        df_temp   = mapping.ListDataFrames(mxd_temp)[0]
        mapping.AddLayer(df_temp, lyr, "TOP")
        lyr_ref = mapping.ListLayers(mxd_temp)[0]
        xml_renderer = lyr_ref._arc_object.renderer
        mapping.RemoveLayer(df_temp, lyr_ref)

        # Extrai blocos de cada UniqueValueInfo do XML
        blocos = re.findall(
            r'<UniqueValueInfo[^>]*>.*?</UniqueValueInfo>',
            xml_renderer, re.DOTALL
        )
        for bloco in blocos:
            # Valor
            val_m = re.search(r'<Value>(.*?)</Value>', bloco)
            if not val_m:
                continue
            valor = val_m.group(1).strip()

            # Usa o NOME_UNIDA completo da tabela em vez da sigla
            rotulo = NOMES_SIGLA.get(valor, valor)

            # Cor RGB (primeira ocorrencia no bloco = cor de preenchimento)
            r_m = re.search(r'<Red>(\d+)</Red>', bloco)
            g_m = re.search(r'<Green>(\d+)</Green>', bloco)
            b_m = re.search(r'<Blue>(\d+)</Blue>', bloco)

            if r_m and g_m and b_m:
                r = int(r_m.group(1))
                g = int(g_m.group(1))
                b = int(b_m.group(1))
            else:
                r, g, b = 200, 200, 200  # fallback cinza

            cores[valor] = (r, g, b, rotulo)

        print("  {} cores lidas do XML do renderer.".format(len(cores)))
    except Exception as e:
        print("ERRO ao ler .lyr: {}".format(e))
    return cores

# =============================================================================
# GERA LEGENDA COM PIL
# =============================================================================

def gerar_legenda_png(grupo, siglas, cores_dict, caminho_png):
    itens = []
    for sigla in siglas:
        if sigla in cores_dict:
            r, g, b, rotulo = cores_dict[sigla]
            itens.append((r, g, b, rotulo))

    if not itens:
        print("  AVISO: Nenhuma classe encontrada no .lyr para este grupo.")
        return False

    try:
        fonte_titulo = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", LEG_FONTE_TIT)
        fonte_item   = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf",   LEG_FONTE_ITM)
    except:
        fonte_titulo = ImageFont.load_default()
        fonte_item   = ImageFont.load_default()

    altura_titulo = LEG_FONTE_TIT + LEG_ESPACO * 2
    altura_item   = LEG_CAIXA_H + LEG_ESPACO
    altura_total  = LEG_MARGEM + altura_titulo + len(itens) * altura_item + LEG_MARGEM

    img  = Image.new("RGB", (LEG_LARGURA, altura_total), COR_FUNDO)
    draw = ImageDraw.Draw(img)

    # Título
    draw.text((LEG_MARGEM, LEG_MARGEM), grupo,
              font=fonte_titulo, fill=COR_TEXTO)

    y = LEG_MARGEM + altura_titulo
    for (r, g, b, rotulo) in itens:
        draw.rectangle(
            [LEG_MARGEM, y, LEG_MARGEM + LEG_CAIXA_W, y + LEG_CAIXA_H],
            fill=(r, g, b), outline=COR_BORDA
        )
        draw.text(
            (LEG_MARGEM + LEG_CAIXA_W + 20, y + (LEG_CAIXA_H - LEG_FONTE_ITM) // 2),
            rotulo, font=fonte_item, fill=COR_TEXTO
        )
        y += altura_item

    img.save(caminho_png, dpi=(300, 300))
    print("    >> {}".format(os.path.basename(caminho_png)))
    return True

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 65)
    print("GERANDO 4 PNGs POR GRUPO → 2 PASTAS")
    print("=" * 65)

    for caminho, label in [
        (K_RASTER, "K_RASTER"), (K_LYR, "K_LYR"),
        (MXD_BASE, "MXD_BASE"), (LITO_LYR, "LITO_LYR"),
    ]:
        if not arcpy.Exists(caminho):
            print("ERRO: {} nao encontrado:\n  {}".format(label, caminho))
            return

    arcpy.env.overwriteOutput = True
    criar_pasta(PASTA_FINAL)

    # Lê cores do .lyr uma vez
    print("Lendo cores do .lyr...")
    cores_dict = ler_cores_lyr(LITO_LYR)
    print("  {} classes lidas.".format(len(cores_dict)))

    # Carrega MXD base
    mxd = mapping.MapDocument(MXD_BASE)
    df  = mapping.ListDataFrames(mxd)[0]
    try:
        df.frame.borderWidth = 0
    except:
        pass

    lyr_to    = mapping.ListLayers(mxd, NOME_LAYER_TO,    df)[0]
    lyr_sedes = mapping.ListLayers(mxd, NOME_LAYER_SEDES, df)[0]

    # Extensão do estado
    ext_to = arcpy.Describe(lyr_to).extent
    dx_to  = (ext_to.XMax - ext_to.XMin) * 0.02
    dy_to  = (ext_to.YMax - ext_to.YMin) * 0.02
    EXTENT_ESTADO = arcpy.Extent(
        ext_to.XMin - dx_to, ext_to.YMin - dy_to,
        ext_to.XMax + dx_to, ext_to.YMax + dy_to
    )

    # Adiciona raster K completo UMA VEZ (sem recortar — é RGB)
    lyr_k      = mapping.Layer(K_LYR)
    lyr_k.name = "K_FULL"
    mapping.AddLayer(df, lyr_k, "BOTTOM")
    lyr_k_ref  = mapping.ListLayers(mxd, "K_FULL", df)[0]
    lyr_k_ref.visible = False

    relatorio = []

    for grupo, siglas in GRUPOS.items():
        print("\n" + "-" * 55)
        print(">>> {}".format(grupo))

        pasta_shapes_grupo = os.path.join(PASTA_SHAPES, grupo)
        pasta_final_grupo  = os.path.join(PASTA_FINAL,  grupo)

        if not os.path.exists(pasta_shapes_grupo):
            print("  AVISO: Pasta shapes nao encontrada.")
            relatorio.append((grupo, "SEM PASTA"))
            continue

        shp = encontrar_shp(pasta_shapes_grupo)
        if not shp:
            print("  AVISO: lito_*.shp nao encontrado.")
            relatorio.append((grupo, "SEM SHP"))
            continue

        criar_pasta(pasta_final_grupo)
        nome = nf(grupo)

        # Adiciona litologia com simbologia do .lyr
        lyr_lito      = mapping.Layer(shp)
        lyr_lito.name = "LITO_TEMP"
        mapping.AddLayer(df, lyr_lito, "TOP")
        lyr_lito_ref  = mapping.ListLayers(mxd, "LITO_TEMP", df)[0]
        try:
            mapping.UpdateLayer(df, lyr_lito_ref,
                                mapping.Layer(LITO_LYR), symbology_only=True)
        except Exception as e:
            print("  AVISO simbologia lito: {}".format(e))

        # Atualiza refs
        lyr_to    = mapping.ListLayers(mxd, NOME_LAYER_TO,    df)[0]
        lyr_sedes = mapping.ListLayers(mxd, NOME_LAYER_SEDES, df)[0]
        lyr_k_ref = mapping.ListLayers(mxd, "K_FULL",         df)[0]

        # --------------------------------------------------------------
        # PNG 1 — Litologia + Sedes | sem limite_TO | zoom grupo
        # --------------------------------------------------------------
        lyr_lito_ref.visible = True
        lyr_sedes.visible    = True
        lyr_to.visible       = False
        lyr_k_ref.visible    = False

        zoom_grupo(df, lyr_lito_ref)
        p1 = os.path.join(pasta_shapes_grupo, "1_lito_sem_estado_{}.png".format(nome))
        exportar_png(mxd, p1)
        salvar_nas_duas_pastas(p1, pasta_shapes_grupo, pasta_final_grupo)

        # --------------------------------------------------------------
        # PNG 2 — Litologia + limite_TO | sem Sedes | zoom estado
        # --------------------------------------------------------------
        lyr_lito_ref.visible = True
        lyr_to.visible       = True
        lyr_sedes.visible    = False
        lyr_k_ref.visible    = False

        df.extent = EXTENT_ESTADO
        p2 = os.path.join(pasta_shapes_grupo, "2_lito_com_estado_{}.png".format(nome))
        exportar_png(mxd, p2)
        salvar_nas_duas_pastas(p2, pasta_shapes_grupo, pasta_final_grupo)

        # --------------------------------------------------------------
        # PNG 3 — Raster K recortado | sem Sedes | sem limite_TO
        # SOLUCAO RGB: recorta banda a banda com Con para substituir
        # NoData por 255 (branco) em cada banda, depois compoe de volta
        # --------------------------------------------------------------
        lyr_lito_ref.visible = False
        lyr_to.visible       = False
        lyr_sedes.visible    = False
        lyr_k_ref.visible    = False

        k_recortado = os.path.join(pasta_shapes_grupo, "K_{}.tif".format(nome))

        try:
            # -------------------------------------------------------
            # Remove do MXD qualquer layer K anterior que esteja
            # bloqueando o arquivo no disco
            # -------------------------------------------------------
            for lyr_old in mapping.ListLayers(mxd, "K_REC_TEMP", df):
                mapping.RemoveLayer(df, lyr_old)
            if arcpy.Exists(k_recortado):
                try:
                    arcpy.Delete_management(k_recortado)
                except:
                    pass

            arcpy.CheckOutExtension("Spatial")

            # Recorta banda a banda e substitui NoData por 255 (branco)
            arcpy.env.mask = ""
            tmp_dir = pasta_shapes_grupo

            for i, banda in enumerate(["Band_1", "Band_2", "Band_3"], 1):
                b = arcpy.sa.ExtractByMask(
                    arcpy.sa.Raster("{}\{}".format(K_RASTER, banda)), shp)
                b_fill = arcpy.sa.Con(arcpy.sa.IsNull(b), 255, b)
                b_fill.save(os.path.join(tmp_dir, "_tmp_b{}.tif".format(i)))

            arcpy.CheckInExtension("Spatial")

            # Recompoe RGB
            tmp1 = os.path.join(tmp_dir, "_tmp_b1.tif")
            tmp2 = os.path.join(tmp_dir, "_tmp_b2.tif")
            tmp3 = os.path.join(tmp_dir, "_tmp_b3.tif")
            arcpy.CompositeBands_management(
                "{};{};{}".format(tmp1, tmp2, tmp3), k_recortado)

            # Limpa temporarios de banda
            for tmp in [tmp1, tmp2, tmp3]:
                try:
                    arcpy.Delete_management(tmp)
                except:
                    pass

            # Adiciona ao MXD com simbologia do .lyr e exporta
            lyr_k_rec      = mapping.Layer(k_recortado)
            lyr_k_rec.name = "K_REC_TEMP"
            mapping.AddLayer(df, lyr_k_rec, "BOTTOM")
            lyr_k_rec_ref  = mapping.ListLayers(mxd, "K_REC_TEMP", df)[0]

            try:
                mapping.UpdateLayer(df, lyr_k_rec_ref,
                                    mapping.Layer(K_LYR), symbology_only=True)
            except Exception as e:
                print("  AVISO simbologia K: {}".format(e))

            zoom_grupo(df, lyr_lito_ref)
            p3 = os.path.join(pasta_shapes_grupo, "3_K_{}.png".format(nome))
            exportar_png(mxd, p3)
            salvar_nas_duas_pastas(p3, pasta_shapes_grupo, pasta_final_grupo)

            # Remove do MXD imediatamente apos exportar
            mapping.RemoveLayer(df, lyr_k_rec_ref)

        except Exception as e:
            print("  ERRO ao recortar K: {}".format(e))

        # --------------------------------------------------------------
        # PNG 4 — Legenda (PIL, cores do .lyr)
        # --------------------------------------------------------------
        p4 = os.path.join(pasta_shapes_grupo, "4_legenda_{}.png".format(nome))
        ok_leg = gerar_legenda_png(grupo, siglas, cores_dict, p4)
        if ok_leg:
            salvar_nas_duas_pastas(p4, pasta_shapes_grupo, pasta_final_grupo)

        # Remove litologia temporária
        mapping.RemoveLayer(df, lyr_lito_ref)

        # Restaura camadas base
        lyr_to    = mapping.ListLayers(mxd, NOME_LAYER_TO,    df)[0]
        lyr_sedes = mapping.ListLayers(mxd, NOME_LAYER_SEDES, df)[0]
        lyr_to.visible    = True
        lyr_sedes.visible = True

        relatorio.append((grupo, "OK"))
        print("  OK — 4 PNGs em ambas as pastas.")

    # Remove K do MXD
    for l in mapping.ListLayers(mxd, "K_FULL", df):
        mapping.RemoveLayer(df, l)

    # ------------------------------------------------------------------
    # RELATÓRIO
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("RELATORIO FINAL")
    print("=" * 65)
    ok  = [r for r in relatorio if r[1] == "OK"]
    err = [r for r in relatorio if r[1] != "OK"]
    print("Grupos exportados: {}/{}".format(len(ok), len(relatorio)))
    if err:
        print("\nProblemas:")
        for nome, status in err:
            print("  [{:<12}] {}".format(status, nome))
    print("\nShapes + imagens: {}".format(PASTA_SHAPES))
    print("Somente imagens:  {}".format(PASTA_FINAL))
    print("Script concluido!")


if __name__ == "__main__":
    main()
else:
    main()