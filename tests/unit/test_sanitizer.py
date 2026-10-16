"""
Testes Unitarios do Sanitizador Central de Logs e Payloads LGPD (core/sanitizer.py).
Valida que identificadores tecnicos (UUIDs, action_id, tool_call_id) nao sofram falsos positivos
de redacao de CPF, enquanto dados pessoais autenticos permanecem devidamente anonimizados.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import uuid
from pydantic import ValidationError
from core.sanitizer import (
    CentralLogSanitizer,
    central_log_sanitizer,
    sanitize_dict,
    sanitize_text,
    is_valid_cpf,
    REDACTED_CPF,
)
from core.schemas.genui import (
    GenUIActionOption,
    BasketUpsellStrategyProps,
    UpsellComboItem,
)


def test_cpf_validation_checksum():
    """Valida o calculo do digito verificador modulo 11 da Receita Federal."""
    # CPFs validos matematicamente
    assert is_valid_cpf("52998224725") is True
    # CPFs com todos digitos iguais sao invalidos
    assert is_valid_cpf("11111111111") is False
    assert is_valid_cpf("00000000000") is False
    # CPFs com DV corrompido
    assert is_valid_cpf("52998224720") is False


def test_formatted_cpf_redaction():
    """Valida que CPFs formatados no padrao XXX.XXX.XXX-XX sao devidamente redigidos."""
    texto = "O cliente com CPF 529.982.247-25 solicitou cupom fiscal no caixa."
    limpo, counts = central_log_sanitizer.sanitize_text(texto)
    assert REDACTED_CPF in limpo
    assert "529.982.247-25" not in limpo
    assert counts.get("cpf", 0) == 1


def test_unformatted_cpf_redaction():
    """Valida que CPFs nao formatados isolados com DV valido sao redigidos."""
    texto = "Documento informado: 52998224725 para emissao NFC-e."
    limpo, counts = central_log_sanitizer.sanitize_text(texto)
    assert REDACTED_CPF in limpo
    assert "52998224725" not in limpo
    assert counts.get("cpf", 0) == 1


def test_unformatted_invalid_cpf_not_redacted():
    """Valida que sequencias numericas de 11 digitos que nao sao CPFs validos nao sao alteradas."""
    numero_qualquer = "12345678900"
    texto = f"Numero do protocolo de atendimento: {numero_qualquer}."
    limpo, counts = central_log_sanitizer.sanitize_text(texto)
    assert numero_qualquer in limpo
    assert counts.get("cpf", 0) == 0


def test_uuid_with_embedded_valid_cpf_not_redacted():
    """
    Garante que UUIDs RFC 4122 (mesmo com sequencia de 11 digitos que satisfaz
    a formula matematica do CPF da Receita) nunca sofram redacao indevida.
    """
    # 52998224725 e matematicamente valido, mas dentro do UUID e apenas um identificador
    uuid_com_cpf = "act_9f94f03c-8ca4-4f9e-a9a5-52998224725a"
    limpo, counts = central_log_sanitizer.sanitize_text(uuid_com_cpf)
    assert limpo == uuid_com_cpf
    assert counts.get("cpf", 0) == 0

    # Teste com UUID puro sem prefixo
    uuid_puro = "9f94f03c-8ca4-4f9e-a9a5-52998224725a"
    limpo_puro, counts_puro = central_log_sanitizer.sanitize_text(uuid_puro)
    assert limpo_puro == uuid_puro
    assert counts_puro.get("cpf", 0) == 0

    # Teste com tool_call_id
    tool_call = "call_52998224725b-8ca4-4f9e-a9a5-1234567890ab"
    limpo_tool, counts_tool = central_log_sanitizer.sanitize_text(tool_call)
    assert limpo_tool == tool_call
    assert counts_tool.get("cpf", 0) == 0


def test_sanitize_dict_preserves_structural_action_and_tool_ids():
    """Valida que sanitize_dict preserva intactas chaves como action_id e tool_call_id."""
    payload = {
        "status": "ok",
        "action_id": "act_9f94f03c-8ca4-4f9e-a9a5-78491823901a",
        "tool_call_id": "call_11112222-3333-4444-5555-666677778888",
        "component_name": "render_BasketUpsellStrategyUI",
        "client_component": "BasketUpsellStrategyUI",
        "usuario": {
            "nome": "Carlos Silva",
            "cpf": "52998224725",
        },
    }

    limpo, counts = sanitize_dict(payload)
    # action_id e tool_call_id preservados
    assert limpo["action_id"] == "act_9f94f03c-8ca4-4f9e-a9a5-78491823901a"
    assert limpo["tool_call_id"] == "call_11112222-3333-4444-5555-666677778888"
    assert limpo["component_name"] == "render_BasketUpsellStrategyUI"
    assert limpo["client_component"] == "BasketUpsellStrategyUI"
    # CPF do usuario devidamente redigido
    assert limpo["usuario"]["cpf"] == REDACTED_CPF
    assert counts.get("cpf", 0) == 1


def test_pydantic_genui_action_option_after_sanitization():
    """Valida que um objeto GenUIActionOption permanece estritamente valido apos sanitizacao."""
    action_id_critico = "act_9f94f03c-8ca4-4f9e-a9a5-52998224725a"
    action = GenUIActionOption(
        action_id=action_id_critico,
        label="Simular no Canvas",
        action_type="inspection",
        variant="ghost",
        is_destructive=False,
        requires_confirmation=False,
        payload={"intent": "conveniencia_vendas_cruzadas"},
    )

    action_dict = action.model_dump(mode="json")
    limpo, _ = sanitize_dict(action_dict)

    # Nao deve levantar ValidationError
    action_recriado = GenUIActionOption(**limpo)
    assert action_recriado.action_id == action_id_critico


def test_basket_upsell_props_after_sanitization():
    """Valida que BasketUpsellStrategyProps completo pode ser sanitizado e desserializado sem erros."""
    action_id_1 = "act_9f94f03c-8ca4-4f9e-a9a5-52998224725a"
    action_id_2 = f"act_{uuid.uuid4()}"

    props = BasketUpsellStrategyProps(
        diagnosis="Oportunidade de cross-selling entre cafe e pao de queijo no balcao do PDV.",
        confidence_score=0.92,
        projected_ticket_increase=8.50,
        top_combos=[
            UpsellComboItem(
                anchor_product="Cafe Expresso",
                recommended_product="Pao de Queijo",
                lift=3.2,
                confidence_pct=48.0,
                support_pct=15.0,
                additional_ticket_reais=7.50,
                script_pitch="Ofereca pao de queijo quentinho para acompanhar o cafe.",
            )
        ],
        suggested_actions=[
            GenUIActionOption(
                action_id=action_id_1,
                label="Ativar Combo PDV",
                action_type="mutation",
            ),
            GenUIActionOption(
                action_id=action_id_2,
                label="Simular no Canvas",
                action_type="inspection",
            ),
        ],
    )

    props_dict = props.model_dump(mode="json")
    props_sanitizado, _ = sanitize_dict(props_dict)

    # Reconstituicao via Pydantic v2
    reconstruido = BasketUpsellStrategyProps(**props_sanitizado)
    assert len(reconstruido.suggested_actions) == 2
    assert reconstruido.suggested_actions[0].action_id == action_id_1
    assert reconstruido.suggested_actions[1].action_id == action_id_2
