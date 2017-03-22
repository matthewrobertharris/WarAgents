package readers;

import java.util.List;

import model.output.Action;
import model.output.Action.Activity;

public interface ActionReader {

	public Action readAction(List<String> values);
	public Activity readActivity(String activity);
}
