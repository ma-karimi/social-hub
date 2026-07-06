from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from social_hub.api.deps import (
    TenantContextDep,
    get_delete_service,
    get_edit_service,
    get_post_repo,
    get_publication_repo,
    get_publish_service,
)
from social_hub.api.schemas.posts import (
    EditPostRequest,
    PostResponse,
    PublicationStatusSchema,
    PublishNormalRequest,
    PublishProductRequest,
    PublishResponse,
)
from social_hub.application.services.delete_service import DeleteService
from social_hub.application.services.edit_service import EditService
from social_hub.application.services.publish_service import PublishService
from social_hub.domain.entities.post import PostContent
from social_hub.domain.exceptions import (
    CapabilityNotSupportedError,
    ConnectionNotFoundError,
    DuplicatePostError,
    PostNotFoundError,
)
from social_hub.domain.value_objects.platform_type import PlatformType

router = APIRouter()


@router.post("/publish-product", response_model=PublishResponse, status_code=status.HTTP_202_ACCEPTED)
async def publish_product(
    body: PublishProductRequest,
    tenant_ctx: TenantContextDep,
    publish_service: Annotated[PublishService, Depends(get_publish_service)],
):
    try:
        platforms = [PlatformType(p) for p in body.platforms]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    content = PostContent(
        title=body.content.title,
        body=body.content.body,
        price=body.content.price,
        currency=body.content.currency,
        images=body.content.images,
        metadata=body.content.metadata,
    )
    buttons_data = [b.model_dump() for b in body.buttons]

    try:
        result = await publish_service.publish_product(
            tenant_ctx=tenant_ctx,
            platforms=platforms,
            content=content,
            buttons_data=buttons_data,
            external_ref=body.external_ref,
        )
    except DuplicatePostError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ConnectionNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return PublishResponse(
        post_id=result["post_id"],
        publications=[PublicationStatusSchema(**p) for p in result["publications"]],
        warnings=result["warnings"],
    )


@router.post("/publish", response_model=PublishResponse, status_code=status.HTTP_202_ACCEPTED)
async def publish_normal(
    body: PublishNormalRequest,
    tenant_ctx: TenantContextDep,
    publish_service: Annotated[PublishService, Depends(get_publish_service)],
):
    try:
        platforms = [PlatformType(p) for p in body.platforms]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    content = PostContent(
        title=body.content.title,
        body=body.content.body,
        price=body.content.price,
        currency=body.content.currency,
        images=body.content.images,
        metadata=body.content.metadata,
    )

    try:
        result = await publish_service.publish_normal(
            tenant_ctx=tenant_ctx,
            platforms=platforms,
            content=content,
            external_ref=body.external_ref,
        )
    except DuplicatePostError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ConnectionNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return PublishResponse(
        post_id=result["post_id"],
        publications=[PublicationStatusSchema(**p) for p in result["publications"]],
        warnings=result["warnings"],
    )


@router.patch("/{post_id}", response_model=PublishResponse, status_code=status.HTTP_202_ACCEPTED)
async def edit_post(
    post_id: UUID,
    body: EditPostRequest,
    tenant_ctx: TenantContextDep,
    edit_service: Annotated[EditService, Depends(get_edit_service)],
):
    new_content = PostContent(
        title=body.content.title,
        body=body.content.body,
        price=body.content.price,
        currency=body.content.currency,
        images=body.content.images,
        metadata=body.content.metadata,
    )

    try:
        result = await edit_service.edit_post(
            tenant_ctx=tenant_ctx,
            post_id=post_id,
            new_content=new_content,
        )
    except PostNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return PublishResponse(
        post_id=result["post_id"],
        publications=[],
        warnings=result["warnings"],
    )


@router.delete("/{post_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_post(
    post_id: UUID,
    tenant_ctx: TenantContextDep,
    delete_service: Annotated[DeleteService, Depends(get_delete_service)],
):
    try:
        result = await delete_service.delete_post(
            tenant_ctx=tenant_ctx,
            post_id=post_id,
        )
    except PostNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"detail": "Delete enqueued", "publication_count": result["delete_enqueued"]}


@router.get("/{post_id}", response_model=PostResponse)
async def get_post_status(
    post_id: UUID,
    tenant_ctx: TenantContextDep,
    post_repo=Depends(get_post_repo),
    publication_repo=Depends(get_publication_repo),
):
    post = await post_repo.get_by_id(tenant_ctx.tenant_id, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    publications = await publication_repo.list_by_post(post.id)

    return PostResponse(
        id=str(post.id),
        tenant_id=str(post.tenant_id),
        post_type=post.post_type,
        status=post.status,
        external_ref=post.external_ref,
        publications=[
            PublicationStatusSchema(
                id=str(p.id),
                status=p.status,
                connection_id=str(p.connection_id),
            )
            for p in publications
        ],
    )


@router.get("", response_model=list[PostResponse])
async def list_posts(
    tenant_ctx: TenantContextDep,
    post_repo=Depends(get_post_repo),
    limit: int = 50,
    offset: int = 0,
):
    posts = await post_repo.list_by_tenant(tenant_ctx.tenant_id, limit=limit, offset=offset)
    return [
        PostResponse(
            id=str(p.id),
            tenant_id=str(p.tenant_id),
            post_type=p.post_type,
            status=p.status,
            external_ref=p.external_ref,
        )
        for p in posts
    ]
