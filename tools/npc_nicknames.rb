# encoding: UTF-8
# Only game-authored NPC teams pass through this factory. Never translate Pokemon#name globally.
module FireAshZHTW::TrainerNicknames
  def to_trainer
    trainer = super
    if FireAshZHTW.active?
      trainer.party.each do |pokemon|
        next unless pokemon.nicknamed?
        nickname = FireAshZHTW::NPC_NICKNAMES[pokemon.name]
        pokemon.name = nickname if nickname
      end
    end
    trainer
  end
end
# ZUD and Randomized Trainer Teams redefine this method after the main archive loads.
GameData::Trainer.prepend(FireAshZHTW::TrainerNicknames)
