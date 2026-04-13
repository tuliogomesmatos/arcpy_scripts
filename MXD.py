# =============================================================================
#  SCRIPT: Atualizar MXD com Shapefiles do CAR
#  ArcGIS 10.8 / ArcMap - arcpy + arcpy.mapping
#
#  O QUE FAZ:
#   1. Lê os shapefiles do CAR na pasta informada
#   2. Atualiza os data sources das camadas no MXD template
#   3. Calcula área (ha) de cada camada via geometria
#   4. Atualiza elementos de texto da legenda no layout
#   5. Atualiza Município e Área da Propriedade
#   6. Salva cópia do MXD com nome da pasta do projeto
# =============================================================================

import arcpy
import arcpy.mapping as mapping
import os

# =============================================================================
#  CONFIGURAÇÕES — edite apenas este bloco
# =============================================================================

# Pasta contendo os shapefiles do CAR
PASTA_CAR = r"G:\Meu Drive\CLIENTES\ANDERSON - MIRACEMA\FAZENDA ITAICI (PAI DO ANDERSON)\sig\SHAPES_783183"

# Caminho do template MXD (o que você usa sempre)
TEMPLATE_MXD = r"C:\Tulio\CAR.mxd"

# Pasta onde o MXD atualizado será salvo
PASTA_SAIDA = r"G:\Meu Drive\CLIENTES\ANDERSON - MIRACEMA\FAZENDA ITAICI (PAI DO ANDERSON)\sig"

# Nome do município (atualizar conforme o projeto)
# Deixe como "" para preencher manualmente depois
MUNICIPIO = "MIRACEMA DO TOCANTINS - TO"

# =============================================================================
#  MAPEAMENTO: nome do shapefile (sem extensão) → informações da camada
#
#  Estrutura de cada entrada:
#    "NOME_DO_SHP": {
#        "layer_name": nome exato da camada no MXD,
#        "legenda_sigla": sigla exibida na legenda (None = não entra na legenda),
#        "texto_area_elem": nome do elemento de texto que exibe a área no layout
#    }
# =============================================================================
MAPEAMENTO = {
    "1_AREA_IMOVEL_CALCULADO": {
        "layer_name": "1_AREA_IMOVEL_CALCULADO",
        "legenda_sigla": "APR",
        "texto_area_elem": "txt_area_APR"   # nome do elemento de texto no MXD
    },
    "2_VEGETACAO_NATIVA_CALCULADO": {
        "layer_name": "2_VEGETACAO_NATIVA_CALCULADO",
        "legenda_sigla": "ARVN",
        "texto_area_elem": "txt_area_ARVN"
    },
    "5_AREA_USO_ALTERNATIVO_CALCULADO": {
        "layer_name": "5_AREA_USO_ALTERNATIVO_CALCULAD",  # ArcMap limita 30 chars
        "legenda_sigla": "AUA",
        "texto_area_elem": "txt_area_AUA"
    },
    "10_HIDROGRAFIA_IMOVEL_CALCULADO": {
        "layer_name": "10_HIDROGRAFIA_IMOVEL_CALCULADO",
        "legenda_sigla": "HD",
        "texto_area_elem": "txt_area_HD"
    },
    "11_APP_TOTAL_CALCULADO": {
        "layer_name": "11_APP_TOTAL_CALCULADO",
        "legenda_sigla": "APP",
        "texto_area_elem": "txt_area_APP"
    },
    "16_ARL_SUPLEMENTAR_CALCULADO": {
        "layer_name": "16_ARL_SUPLEMENTAR_CALCULADO",
        "legenda_sigla": "ARLS",
        "texto_area_elem": "txt_area_ARLS"
    },
    "17_ARL_TOTAL_CALCULADO": {
        "layer_name": "17_ARL_TOTAL_CALCULADO",
        "legenda_sigla": "ARL",
        "texto_area_elem": "txt_area_ARL"
    },
}

# Nomes dos elementos de texto no layout para município e área total
ELEM_MUNICIPIO   = "txt_municipio"       # ex: "MUNICÍPIOS: MIRACEMA DO TOCANTINS - TO"
ELEM_AREA_TOTAL  = "txt_area_propriedade"  # ex: "ÁREA DA PROPRIEDADE: 49,9265 ha"

# =============================================================================
#  FUNÇÕES AUXILIARES
# =============================================================================

def calcular_area_ha(shapefile_path):
    """
    Calcula a soma das áreas de todas as feições do shapefile em hectares.
    Usa arcpy.da.SearchCursor com SHAPE@AREA (retorna m²) e converte para ha.
    """
    total_m2 = 0.0
    try:
        with arcpy.da.SearchCursor(shapefile_path, ["SHAPE@AREA"]) as cursor:
            for row in cursor:
                if row[0] is not None:
                    total_m2 += row[0]
    except Exception as e:
        print("  [AVISO] Erro ao calcular area de {}: {}".format(shapefile_path, e))
        return None

    area_ha = total_m2 / 10000.0
    return area_ha


def formatar_area(area_ha):
    """
    Formata área em hectares no padrão brasileiro: 49,9265
    4 casas decimais, vírgula como separador decimal.
    """
    if area_ha is None:
        return "0,0000"
    return "{:.4f}".format(area_ha).replace(".", ",")


def listar_elementos_texto(mxd):
    """Lista todos os elementos de texto do layout (útil para debug)."""
    elems = mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")
    print("\n  Elementos de texto encontrados no MXD:")
    for e in elems:
        print("    Nome: '{}'  |  Texto: '{}'".format(e.name, e.text))


def atualizar_datasource_camada(mxd, layer_name, novo_workspace, novo_dataset):
    """
    Atualiza o data source de uma camada específica no MXD.
    novo_workspace: pasta contendo o shapefile
    novo_dataset: nome do shapefile SEM extensão
    """
    layers = mapping.ListLayers(mxd)
    for lyr in layers:
        if lyr.name == layer_name:
            if lyr.supports("DATASOURCE"):
                try:
                    lyr.replaceDataSource(novo_workspace, "SHAPEFILE_WORKSPACE", novo_dataset)
                    print("  [OK] Datasource atualizado: {}".format(layer_name))
                    return True
                except Exception as e:
                    print("  [ERRO] Falha ao atualizar datasource de '{}': {}".format(layer_name, e))
                    return False
    print("  [AVISO] Camada '{}' nao encontrada no MXD.".format(layer_name))
    return False


def atualizar_texto_elemento(mxd, nome_elemento, novo_texto):
    """
    Atualiza o texto de um elemento de texto do layout pelo nome.
    """
    elems = mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", nome_elemento)
    if elems:
        elems[0].text = novo_texto
        print("  [OK] Elemento '{}' atualizado: {}".format(nome_elemento, novo_texto))
    else:
        print("  [AVISO] Elemento de texto '{}' nao encontrado no layout.".format(nome_elemento))


# =============================================================================
#  EXECUÇÃO PRINCIPAL
# =============================================================================

def main():
    print("=" * 60)
    print("  ATUALIZACAO MXD - CAR")
    print("=" * 60)

    # Valida caminhos
    if not os.path.exists(PASTA_CAR):
        print("[ERRO] Pasta CAR nao encontrada: {}".format(PASTA_CAR))
        return
    if not os.path.exists(TEMPLATE_MXD):
        print("[ERRO] Template MXD nao encontrado: {}".format(TEMPLATE_MXD))
        return
    if not os.path.exists(PASTA_SAIDA):
        os.makedirs(PASTA_SAIDA)
        print("[INFO] Pasta de saida criada: {}".format(PASTA_SAIDA))

    # Nome do projeto = nome da pasta CAR
    nome_projeto = os.path.basename(PASTA_CAR.rstrip("\\/"))
    mxd_saida = os.path.join(PASTA_SAIDA, "{}.mxd".format(nome_projeto))

    # Abre o template MXD
    print("\n[1] Abrindo template MXD...")
    mxd = mapping.MapDocument(TEMPLATE_MXD)

    # (Opcional) Lista elementos de texto para identificar nomes — descomente para debug:
    # listar_elementos_texto(mxd)

    # Dicionário para guardar áreas calculadas
    areas_ha = {}

    print("\n[2] Atualizando datasources e calculando areas...")
    for shp_base, config in MAPEAMENTO.items():
        shp_path = os.path.join(PASTA_CAR, shp_base + ".shp")

        if not os.path.exists(shp_path):
            print("  [AVISO] Shapefile nao encontrado: {}".format(shp_path))
            areas_ha[config["legenda_sigla"]] = None
            continue

        print("\n  Processando: {}".format(shp_base))

        # Atualiza datasource no MXD
        atualizar_datasource_camada(mxd, config["layer_name"], PASTA_CAR, shp_base)

        # Calcula área
        area = calcular_area_ha(shp_path)
        sigla = config["legenda_sigla"]
        areas_ha[sigla] = area

        if area is not None:
            print("  [AREA] {} = {} ha".format(sigla, formatar_area(area)))
        else:
            print("  [AVISO] Nao foi possivel calcular area de {}".format(shp_base))

    # Área total da propriedade (camada APR)
    area_apr = areas_ha.get("APR")

    print("\n[3] Atualizando elementos de texto do layout...")

    # Atualiza cada área na legenda
    for shp_base, config in MAPEAMENTO.items():
        sigla = config["legenda_sigla"]
        elem  = config["texto_area_elem"]
        if sigla and elem:
            area_formatada = formatar_area(areas_ha.get(sigla))
            atualizar_texto_elemento(mxd, elem, area_formatada)

    # Atualiza município
    municipio_texto = "MUNICIPIOS: {}".format(MUNICIPIO)
    atualizar_texto_elemento(mxd, ELEM_MUNICIPIO, municipio_texto)

    # Atualiza área da propriedade
    area_prop_texto = "AREA DA PROPRIEDADE: {} ha".format(formatar_area(area_apr))
    atualizar_texto_elemento(mxd, ELEM_AREA_TOTAL, area_prop_texto)

    print("\n[4] Salvando MXD em: {}".format(mxd_saida))
    mxd.saveACopy(mxd_saida)

    print("\n" + "=" * 60)
    print("  CONCLUIDO!")
    print("  MXD salvo em: {}".format(mxd_saida))
    print("=" * 60)

    # Libera objeto MXD
    del mxd


# Ponto de entrada
if __name__ == "__main__":
    main()