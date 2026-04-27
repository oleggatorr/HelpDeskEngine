





# ===================== CREATE =====================

async def create
 
# ===================== READ =====================

async def get_by_id
  

async def get_all


async def list_filtered


# ===================== UPDATE =====================

async def update
 

async def update_stage
 

# ===================== DELETE =====================

async def delete(self, doc_id: int) -> bool:
 

# ===================== EXTRA =====================

async def assign_user(
 

async def archive(self, doc_id: int, user_id: int) -> DocumentResponse:
 

async def unarchive(self, doc_id: int, user_id: int) -> DocumentResponse:


async def lock(self, doc_id: int, user_id: int) -> DocumentResponse:


async def unlock(self, doc_id: int, user_id: int) -> DocumentResponse:
 

async def anonymize(self, doc_id: int, user_id: int) -> DocumentResponse:


async def get_logs(
 