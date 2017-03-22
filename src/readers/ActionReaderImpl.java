package readers;

import java.util.List;

import model.output.Action;
import model.output.Action.Activity;
import model.output.AttackDown;
import model.output.AttackLeft;
import model.output.AttackRight;
import model.output.AttackUp;
import model.output.ChangeTree;
import model.output.ClearPrimary;
import model.output.ClearSecondary;
import model.output.Confused;
import model.output.Death;
import model.output.Defend;
import model.output.DropDirt;
import model.output.DropFood;
import model.output.Eat;
import model.output.LiftDirt;
import model.output.LiftFood;
import model.output.MoveDown;
import model.output.MoveLeft;
import model.output.MoveRight;
import model.output.MoveUp;
import model.output.Reproduce;
import model.output.SetPrimary;
import model.output.SetSecondary;

public class ActionReaderImpl implements ActionReader {


	private PositionReader positionReader;
	
	public ActionReaderImpl(PositionReader positionReader) {
		setPositionReader(positionReader);
	}
	
	public PositionReader getPositionReader() {
		return positionReader;
	}

	public void setPositionReader(PositionReader positionReader) {
		this.positionReader = positionReader;
	}


	@Override
	public Activity readActivity(String activity) {
		return Activity.valueOf(activity);
	}
	
	@Override
	public Action readAction(List<String> values) {
		Activity activity = Activity.valueOf(values.get(0));
		values.remove(0);
		switch(activity) {
		case ATTACK_DOWN:
			return new AttackDown();
		case ATTACK_LEFT:
			return new AttackLeft();
		case ATTACK_RIGHT:
			return new AttackRight();
		case ATTACK_UP:
			return new AttackUp();
		case CHANGE_TREE:
			ChangeTree changeTree = new ChangeTree(values.get(0));
			values.remove(0);
			return changeTree;
		case CONFUSED:
			return new Confused();
		case DEFEND:
			return new Defend();
		case DEATH:
			return new Death();
		case DROP_DIRT:
			return new DropDirt();
		case DROP_FOOD:
			return new DropFood();
		case EAT:
			return new Eat();
		case LIFT_DIRT:
			return new LiftDirt();
		case LIFT_FOOD:
			return new LiftFood();
		case MOVE_DOWN:
			return new MoveDown();
		case MOVE_LEFT:
			return new MoveLeft();
		case MOVE_RIGHT:
			return new MoveRight();
		case MOVE_UP:
			return new MoveUp();
		case REPRODUCE:
			return new Reproduce();
		case SET_PRIMARY:
			return new SetPrimary(getPositionReader().readPosition(values));
		case CLEAR_PRIMARY:
			return new ClearPrimary();
		case SET_SECONDARY:
			return new SetSecondary(getPositionReader().readPosition(values));
		case CLEAR_SECONDARY:
			return new ClearSecondary();
		default:
			return new Confused();
		}
	}
}
