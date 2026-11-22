(() => {
  const form=document.querySelector('[data-review-decision]');
  if (!form) return;
  let dirty=form.dataset.reviewUnsaved==='true';
  form.addEventListener('input',()=>{dirty=true;});
  form.addEventListener('change',()=>{dirty=true;});
  form.addEventListener('submit',event=>queueMicrotask(()=>{if(!event.defaultPrevented)dirty=false;}));
  addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
})();
