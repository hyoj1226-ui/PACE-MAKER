import re

def validate_signup(new_id, new_pw):
    """
    회원가입 조건 검증:
    1. 아이디: 영문(대소문자) 전용
    2. 비밀번호: 영문자 + 숫자 모두 포함 필수
    """
    new_id_clean = new_id.strip()
    new_pw_clean = new_pw.strip()

    if not new_id_clean or not new_pw_clean:
        return False, "아이디와 비밀번호를 모두 입력해 주세요."

    is_id_valid = bool(re.match(r'^[a-zA-Z]+$', new_id_clean))
    if not is_id_valid:
        return False, "아이디는 영문(대소문자)만 사용할 수 있습니다."

    has_letter = bool(re.search(r'[a-zA-Z]', new_pw_clean))
    has_digit = bool(re.search(r'\d', new_pw_clean))
    if not (has_letter and has_digit):
        return False, "비밀번호는 영문자와 숫자를 모두 포함해야 합니다."

    return True, "성공"
